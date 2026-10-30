"""Unit tests for the auth DI wiring (``AuthContainer`` + dep glue).

This module guards the per-provider override surface the rest of the API
test suite relies on. The container must be fully lazy — constructing it
connects to nothing (no Redis/Mongo/SMTP). Each collaborator provider must
be individually overridable via
``app.state.auth_container.<name>.override(providers.Object(fake))`` and the
two FastAPI deps (``auth_dep`` / ``auth_service_dep``) must resolve through
the live container instances so those overrides are honored.
"""

from __future__ import annotations

import types
from datetime import datetime, timezone
from typing import Any

import mongomock
import pytest
from dependency_injector import providers
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

from openwellness_core.adapters.mongo.repositories.mongo_refresh_session_repository import (
    MongoRefreshSessionRepository,
)

from openwellness_api import main
from openwellness_api.auth.service import AuthService
from openwellness_api.config import AppConfig, AuthSettings
from openwellness_api.container import ApplicationContainer
from openwellness_api.deps.auth_container import (
    AuthContainer,
    auth_dep,
    auth_service_dep,
    default_clock,
)


# --------------------------------------------------------------------------- #
# Lightweight fake request plumbing
# --------------------------------------------------------------------------- #
def _make_request(*, auth_container: Any, container: Any = None) -> Any:
    """A minimal stand-in for ``fastapi.Request`` exposing only app.state.

    The deps under test read ``request.app.state.auth_container`` and
    ``request.app.state.container.repositories`` — a SimpleNamespace tree is
    enough; no real FastAPI app is required.
    """
    state = types.SimpleNamespace(auth_container=auth_container, container=container)
    app = types.SimpleNamespace(state=state)
    return types.SimpleNamespace(app=app)


class _FakeRepositories:
    """Stub of ``container.repositories`` exposing user()/participant()."""

    def __init__(self, *, user: Any, participant: Any) -> None:
        self._user = user
        self._participant = participant

    def user(self) -> Any:
        return self._user

    def participant(self) -> Any:
        return self._participant


# --------------------------------------------------------------------------- #
# default_clock
# --------------------------------------------------------------------------- #
def test_default_clock_returns_tz_aware_utc() -> None:
    now = default_clock()
    assert isinstance(now, datetime)
    assert now.tzinfo is not None
    assert now.utcoffset() == timezone.utc.utcoffset(None)


# --------------------------------------------------------------------------- #
# Lazy construction
# --------------------------------------------------------------------------- #
def test_container_construction_is_lazy() -> None:
    """Building the container must NOT connect to Redis/Mongo/SMTP."""
    # If any provider eagerly connected this would raise; it must not.
    # (dependency-injector returns a DynamicContainer instance, so assert on
    # the provider surface rather than class identity.)
    container = AuthContainer()
    assert hasattr(container, "redis_client")
    assert hasattr(container, "otp_store")
    assert hasattr(container, "session_store")
    # Settings singletons are cheap, env-backed objects — safe to resolve.
    assert container.auth_settings() is container.auth_settings()


# --------------------------------------------------------------------------- #
# clock provider returns the callable itself (Object, not invoked)
# --------------------------------------------------------------------------- #
def test_clock_provider_returns_the_callable() -> None:
    container = AuthContainer()
    assert container.clock() is default_clock
    produced = container.clock()()
    assert isinstance(produced, datetime)
    assert produced.tzinfo is not None


# --------------------------------------------------------------------------- #
# Provider override surface (the test override mechanism the suite relies on)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "provider_name",
    ["otp_store", "token_service", "session_store", "email_sender"],
)
def test_provider_override_surface(provider_name: str) -> None:
    container = AuthContainer()
    sentinel = object()
    getattr(container, provider_name).override(providers.Object(sentinel))
    assert getattr(container, provider_name)() is sentinel


# --------------------------------------------------------------------------- #
# auth_dep resolution
# --------------------------------------------------------------------------- #
def test_auth_dep_resolves_overridden_provider() -> None:
    container = AuthContainer()
    sentinel = object()
    container.otp_store.override(providers.Object(sentinel))
    request = _make_request(auth_container=container)

    dep = auth_dep("otp_store")
    assert dep(request) is sentinel


def test_auth_dep_sets_resolver_name() -> None:
    dep = auth_dep("otp_store")
    assert dep.__name__ == "resolve_otp_store"


def test_auth_dep_unknown_provider_raises_runtime_error() -> None:
    container = AuthContainer()
    request = _make_request(auth_container=container)
    dep = auth_dep("does_not_exist")
    with pytest.raises(RuntimeError):
        dep(request)


# --------------------------------------------------------------------------- #
# auth_service_dep assembly (cross-container)
# --------------------------------------------------------------------------- #
def test_auth_service_dep_assembles_from_overrides() -> None:
    container = AuthContainer()

    settings = object()
    otp_store = object()
    token_service = object()
    session_store = object()
    email_sender = object()
    user_repo = object()
    participant_repo = object()

    def clock() -> datetime:
        return datetime.now(timezone.utc)

    container.auth_settings.override(providers.Object(settings))
    container.otp_store.override(providers.Object(otp_store))
    container.token_service.override(providers.Object(token_service))
    container.session_store.override(providers.Object(session_store))
    container.email_sender.override(providers.Object(email_sender))
    # clock is an Object provider whose VALUE is the callable; override with the
    # raw callable wrapped in providers.Object so clock() returns it unchanged.
    container.clock.override(providers.Object(clock))

    repos = _FakeRepositories(user=user_repo, participant=participant_repo)
    main_container = types.SimpleNamespace(repositories=repos)
    request = _make_request(auth_container=container, container=main_container)

    service = auth_service_dep(request)

    assert isinstance(service, AuthService)
    # Inspect the service's stored collaborator references.
    assert service._settings is settings
    assert service._otp_store is otp_store
    assert service._token_service is token_service
    assert service._session_store is session_store
    assert service._email_sender is email_sender
    assert service._user_repo is user_repo
    assert service._participant_repo is participant_repo
    assert service._clock is clock


def test_auth_service_dep_clear_error_when_container_missing() -> None:
    # app.state has no auth_container (e.g. lifespan never wired it / wrong fixture)
    request = _make_request(auth_container=None, container=None)
    with pytest.raises(RuntimeError, match="auth_container is not set"):
        auth_service_dep(request)


# --------------------------------------------------------------------------- #
# redis_client uses decode_responses=True (otp_store hard requirement)
# --------------------------------------------------------------------------- #
def test_redis_client_passes_decode_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_from_url(url: str, **kwargs: Any) -> Any:
        captured["url"] = url
        captured["kwargs"] = kwargs
        return object()

    import redis

    monkeypatch.setattr(redis.Redis, "from_url", staticmethod(fake_from_url))

    container = AuthContainer()
    client = container.redis_client()

    assert client is not None
    assert captured["kwargs"].get("decode_responses") is True
    assert captured["url"] == container.redis_settings().url


# --------------------------------------------------------------------------- #
# Refresh-session repository wiring (composition root)
# --------------------------------------------------------------------------- #
def _app_container() -> ApplicationContainer:
    container = ApplicationContainer()
    container.app_config.override(providers.Object(AppConfig()))
    return container


def test_repository_container_exposes_refresh_session_singleton() -> None:
    repos = _app_container().repositories
    first = repos.refresh_session()
    assert repos.refresh_session() is first
    assert isinstance(first, MongoRefreshSessionRepository)
    assert first._collection.name == "auth_refresh_sessions"


def test_refresh_session_collection_follows_override() -> None:
    repos = _app_container().repositories
    repos.refresh_session_collection.override(providers.Object("custom_sessions"))
    assert repos.refresh_session()._collection.name == "custom_sessions"


def test_auth_settings_refresh_collection_default_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("API_AUTH_REFRESH_COLLECTION", raising=False)
    assert AuthSettings(_env_file=None).refresh_collection == "auth_refresh_sessions"
    monkeypatch.setenv("API_AUTH_REFRESH_COLLECTION", "custom_sessions")
    assert AuthSettings(_env_file=None).refresh_collection == "custom_sessions"


def test_lifespan_wires_refresh_session_repository(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enter the real lifespan: the conftest ``app`` fixture skips it."""
    secret = "x" * 40
    monkeypatch.setenv("API_AUTH_JWT_SECRET", secret)
    monkeypatch.setenv("API_AUTH_CODE_PEPPER", secret)
    monkeypatch.setenv("API_AUTH_REFRESH_COLLECTION", "custom_sessions")
    # Refused at once, so the best-effort startup ping only warns.
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:1/0")

    db = mongomock.MongoClient()["boot"]

    def _factory() -> ApplicationContainer:
        container = ApplicationContainer()
        # No Couchbase connection; initialize/cleanup become no-ops.
        container.repositories.entity_repository.override(providers.Object(MagicMock()))
        container.repositories.collection_repository.override(providers.Object(db))
        return container

    monkeypatch.setattr(main, "ApplicationContainer", _factory)

    app = main.create_app()
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 200
        repo = app.state.container.repositories.refresh_session()
        assert app.state.auth_container.session_store()._repo is repo
        assert repo._collection.name == "custom_sessions"
        assert "uq_token_hash" in db["custom_sessions"].index_information()
