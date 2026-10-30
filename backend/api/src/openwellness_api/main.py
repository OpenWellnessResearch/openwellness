"""FastAPI app factory and entrypoint.

The lifespan builds an :class:`ApplicationContainer`, binds the concrete
``AppConfig`` to the ``app_config`` provider, opens the Couchbase
connection, and wires the resource modules so ``@inject`` markers
resolve. Routes pull repositories through container providers — no
hand-rolled ``app.state.repos`` map.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from dependency_injector import providers
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import APISettings, AppConfig
from .container import ApplicationContainer
from .deps.auth_container import AuthContainer
from .errors.handlers import register_exception_handlers
from .resources import RESOURCE_MODULES
from .v1 import build_v1_router

logger = logging.getLogger(__name__)

_WIRED_MODULES = [mod.__name__ for mod in RESOURCE_MODULES]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # --- Auth feature wiring (settings + boot guard) -------------------- #
    auth_container = AuthContainer()

    # Boot guard (fail fast): refuse to start with weak/unset secrets, BEFORE
    # any expensive setup (no Couchbase/Redis is opened yet), so a misconfigured
    # secret fails instantly. The 32-char minimum also keeps PyJWT's HS256 keys
    # above its weak-key warning threshold. This runs only at real server
    # startup (the test app fixture does not invoke the lifespan), so it can be
    # unconditional.
    s = auth_container.auth_settings()
    if len(s.jwt_secret) < 32 or len(s.code_pepper) < 32:
        raise RuntimeError(
            "API_AUTH_JWT_SECRET and API_AUTH_CODE_PEPPER must each be set to "
            "at least 32 characters."
        )

    # Boot guard passed — now open the expensive resources. The Couchbase
    # cluster opens here (entity_repository().initialize()); from this point on
    # all further setup runs INSIDE the try/ so the finally: always cleans up.
    container = ApplicationContainer()
    container.app_config.override(providers.Object(AppConfig()))
    container.repositories.entity_repository().initialize()
    app.state.container = container
    container.wire(modules=_WIRED_MODULES)

    try:
        # The refresh-session repository is owned by the MAIN container; hand
        # it to the auth container. The collection name is overridden first so
        # a customized API_AUTH_REFRESH_COLLECTION keeps its live sessions. If
        # this (or ensure_indexes / redis construction) raises, the finally:
        # below still cleans up the already-open Couchbase cluster.
        container.repositories.refresh_session_collection.override(providers.Object(s.refresh_collection))
        refresh_repo = container.repositories.refresh_session()
        refresh_repo.ensure_indexes()
        auth_container.refresh_session_repository.override(providers.Object(refresh_repo))

        # Construct/open the Redis client now (lazy provider). Do NOT hard-fail
        # startup if Redis is down — it may come up later, and the per-request
        # 503 handler covers runtime outages. A best-effort ping just surfaces
        # a warning.
        redis_client = auth_container.redis_client()
        try:
            redis_client.ping()
        except Exception:  # pragma: no cover - startup resilience
            logger.warning("Redis not reachable at startup; continuing anyway")

        app.state.auth_container = auth_container

        yield
    finally:
        try:
            container.repositories.entity_repository().cleanup()
        except Exception:  # pragma: no cover - shutdown best-effort
            pass
        try:
            # The redis client may not have been constructed if startup failed
            # before redis_client() was first resolved; guard accordingly.
            auth_container.redis_client().close()
        except Exception:  # pragma: no cover - shutdown best-effort
            pass
        container.unwire()


def create_app() -> FastAPI:
    settings = APISettings()
    app = FastAPI(title=settings.title, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        # Browsers hide non-safelisted response headers from JS unless exposed;
        # the dashboard reads Retry-After for the 429 resend-cooldown fallback.
        expose_headers=["Retry-After"],
    )
    register_exception_handlers(app)
    app.include_router(build_v1_router())

    @app.get("/healthz", tags=["meta"])
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    _ = healthz
    return app


app = create_app()
