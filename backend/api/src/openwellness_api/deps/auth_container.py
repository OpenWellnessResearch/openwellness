"""Auth feature DI wiring: ``AuthContainer`` + FastAPI dep glue.

Mirrors :mod:`openwellness_api.deps.container` for the auth feature. The
:class:`AuthContainer` is a fully lazy ``dependency-injector`` container —
constructing it connects to nothing (Redis/Mongo/SMTP are only touched when
the relevant provider is first resolved). Every collaborator is a
``Singleton`` so the per-provider override surface
(``app.state.auth_container.<name>.override(providers.Object(fake))``) is the
single mechanism the API test suite uses to inject fakes.

The refresh-session repository is owned by the *main* container's
``RepositoryContainer``, so :attr:`AuthContainer.refresh_session_repository` is
a ``Dependency`` placeholder supplied at lifespan time. ``auth_service_dep`` assembles an
:class:`AuthService` per request by reading collaborators off the live
``auth_container`` and the identity repos off the live ``container`` — so any
test override on either container is honored.

This module is pure DI glue: no flow logic, no HTTP routes, and no
``os.environ`` reads beyond what the settings classes already perform.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import redis
from dependency_injector import containers, providers
from fastapi import Request

from openwellness_api.auth.email_sender import SmtpEmailSender
from openwellness_api.auth.otp_store import RedisOtpStore
from openwellness_api.auth.service import AuthService
from openwellness_api.auth.session_store import RefreshSessionStore
from openwellness_api.auth.token_service import JwtTokenService
from openwellness_api.config import AuthSettings, RedisSettings, SmtpSettings


def default_clock() -> datetime:
    """Production clock: a timezone-aware UTC ``datetime``.

    Injected into every collaborator (each expects a
    ``clock: Callable[[], datetime]`` returning tz-aware UTC).
    """
    return datetime.now(timezone.utc)


def _make_redis_client(settings: RedisSettings) -> redis.Redis:
    """Build the prod Redis client with ``decode_responses=True``.

    ``RedisOtpStore`` hard-requires a decode-responses client (a bytes client
    silently breaks every OTP verify), so the requirement lives here where the
    client is constructed rather than relying on a caller remembering it.
    """
    # Bounded timeouts so a Redis outage fails FAST (raising a redis error the
    # 503 handler can map) instead of hanging the request thread for minutes.
    return redis.Redis.from_url(
        settings.url,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5,
    )


class AuthContainer(containers.DeclarativeContainer):
    """Lazy DI container for the email-OTP auth collaborators.

    All providers are lazy: constructing the container connects to nothing.
    """

    auth_settings = providers.Singleton(AuthSettings)
    smtp_settings = providers.Singleton(SmtpSettings)
    redis_settings = providers.Singleton(RedisSettings)

    # The provider's VALUE is the callable itself: ``clock()`` returns
    # ``default_clock`` (collaborators expect a ``Callable[[], datetime]``),
    # NOT the result of invoking it.
    clock = providers.Object(default_clock)

    redis_client = providers.Singleton(_make_redis_client, settings=redis_settings)

    token_service = providers.Singleton(
        JwtTokenService, settings=auth_settings, clock=clock
    )
    otp_store = providers.Singleton(
        RedisOtpStore, redis=redis_client, settings=auth_settings, clock=clock
    )
    email_sender = providers.Singleton(SmtpEmailSender, settings=smtp_settings)

    # Supplied at lifespan time from the main container:
    # ``auth_container.refresh_session_repository.override(providers.Object(repo))``.
    # In tests ``session_store`` is overridden directly, so this is never
    # resolved. ``Factory`` (not ``Singleton``) so the repository is resolved
    # fresh on each call: a resolution before the lifespan override fails
    # immediately instead of caching a broken instance for the process
    # lifetime. The wrapper is cheap (a port + clock).
    refresh_session_repository = providers.Dependency()
    session_store = providers.Factory(
        RefreshSessionStore, repo=refresh_session_repository, clock=clock
    )


def auth_dep(provider_name: str) -> Callable[[Request], Any]:
    """Build a FastAPI dep that pulls a provider from the active auth container.

    Mirrors :func:`openwellness_api.deps.container.container_dep` but over
    ``request.app.state.auth_container``, giving tests the identical override
    surface (``auth_container.<name>.override(...)``).
    """

    def _resolve(request: Request) -> Any:
        container = request.app.state.auth_container
        try:
            provider = getattr(container, provider_name)
        except AttributeError as e:
            raise RuntimeError(
                f"No provider named {provider_name!r} on AuthContainer"
            ) from e
        return provider()

    _resolve.__name__ = f"resolve_{provider_name}"
    return _resolve


def auth_service_dep(request: Request) -> AuthService:
    """Assemble an :class:`AuthService` per request from both containers.

    Auth collaborators come from ``request.app.state.auth_container``; the
    identity repos come from ``request.app.state.container.repositories``.
    Reading through the live container instances means any test override on
    either container is honored. This is the single dependency the router
    uses (``Depends(auth_service_dep)``), keeping the router thin.
    """
    auth_container = getattr(request.app.state, "auth_container", None)
    if auth_container is None:
        raise RuntimeError(
            "app.state.auth_container is not set — the auth container must be "
            "built and attached in the application lifespan (or test fixture)."
        )
    repositories = request.app.state.container.repositories
    return AuthService(
        settings=auth_container.auth_settings(),
        otp_store=auth_container.otp_store(),
        token_service=auth_container.token_service(),
        session_store=auth_container.session_store(),
        email_sender=auth_container.email_sender(),
        user_repo=repositories.user(),
        participant_repo=repositories.participant(),
        clock=auth_container.clock(),
    )
