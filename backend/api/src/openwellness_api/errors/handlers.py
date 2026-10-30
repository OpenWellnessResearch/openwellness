"""Map core domain/adapter exceptions onto AIP-193 HTTP responses."""

import logging

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from pydantic_core import to_jsonable_python
from redis.exceptions import RedisError

from openwellness_core.application.exceptions import (
    DuplicateEntityException,
    LimitExceededException,
)
from openwellness_core.domain.exceptions.domain_exception import (
    DomainException,
    EntityNotFoundException,
    NotFound,
    UnexpectedCount,
)

from .responses import build_error

logger = logging.getLogger(__name__)


def _safe_errors(exc: ValidationError | RequestValidationError) -> list:
    """JSON-safe error details.

    A validation error's ``input`` can be a non-JSON-native value (e.g. a
    ``bson.ObjectId`` from a response-serialization failure); serialize it
    safely so the handler returns a clean 400 instead of crashing while
    rendering the response.
    """
    return to_jsonable_python(exc.errors(), serialize_unknown=True)


def register_exception_handlers(app: FastAPI) -> None:
    """Install handlers on the given app."""

    @app.exception_handler(EntityNotFoundException)
    async def _entity_not_found(_: Request, exc: EntityNotFoundException) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=build_error(404, "NOT_FOUND", str(exc.message)),
        )

    @app.exception_handler(NotFound)
    async def _not_found(_: Request, exc: NotFound) -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=build_error(404, "NOT_FOUND", str(exc.message)),
        )

    @app.exception_handler(UnexpectedCount)
    async def _unexpected_count(_: Request, exc: UnexpectedCount) -> JSONResponse:
        logger.error(
            "UnexpectedCount: expected=%s actual=%s results=%s",
            exc.expected,
            exc.actual,
            exc.results,
        )
        return JSONResponse(
            status_code=500,
            content=build_error(
                500,
                "INTERNAL",
                f"Unexpected result count (expected {exc.expected}, got {exc.actual})",
            ),
        )

    @app.exception_handler(LimitExceededException)
    async def _limit_exceeded(_: Request, exc: LimitExceededException) -> JSONResponse:
        retry_after = max(int(getattr(exc, "retry_after_secs", 3600)), 1)
        return JSONResponse(
            status_code=429,
            headers={"Retry-After": str(retry_after)},
            content=build_error(
                429,
                "RESOURCE_EXHAUSTED",
                str(exc),
                details=[{"retry_after_secs": retry_after}],
            ),
        )

    @app.exception_handler(DuplicateEntityException)
    async def _duplicate_entity(
        _: Request, exc: DuplicateEntityException
    ) -> JSONResponse:
        """409: a write violated a uniqueness constraint.

        The message stays generic because the duplicated value can be an email.
        On POST /v1/users this reveals that an email is registered; ADR 0007
        grants that create to admin only once Phase 2 enforces route auth. The
        /v1/auth:* routes never reach this handler: registration maps the
        exception to the uniform invalid_code 400.
        """
        return JSONResponse(
            status_code=409,
            content=build_error(409, "ALREADY_EXISTS", "The resource already exists."),
        )

    @app.exception_handler(RedisError)
    async def _redis_unavailable(_: Request, exc: RedisError) -> JSONResponse:
        """Map any Redis error (connection/timeout/...) to a clean 503.

        ``RedisError`` is the base class covering ConnectionError/TimeoutError,
        so an OTP-backing Redis outage surfaces as a uniform "temporarily
        unavailable" rather than a 500. Logged at error level by type only — no
        request body, email, or OTP code is ever logged.
        """
        logger.error("Redis unavailable: %s", type(exc).__name__)
        return JSONResponse(
            status_code=503,
            content=build_error(
                503,
                "UNAVAILABLE",
                "The authentication service is temporarily unavailable.",
            ),
        )

    @app.exception_handler(DomainException)
    async def _domain_exception(_: Request, exc: DomainException) -> JSONResponse:
        logger.exception("Unhandled DomainException")
        return JSONResponse(
            status_code=500,
            content=build_error(500, "INTERNAL", str(exc.message)),
        )

    @app.exception_handler(ValidationError)
    async def _pyd_validation(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=build_error(
                400, "INVALID_ARGUMENT", "Validation failed", details=_safe_errors(exc)
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def _request_validation(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=build_error(
                400, "INVALID_ARGUMENT", "Validation failed", details=_safe_errors(exc)
            ),
        )

    @app.exception_handler(HTTPException)
    async def _http_exception(_: Request, exc: HTTPException) -> JSONResponse:
        """Unwrap AIP-193 envelopes raised via ``HTTPException(detail=...)``.

        Helpers (``filter``, ``pagination``, ``time_range``) construct the
        envelope inside ``detail`` so it round-trips through FastAPI's
        exception path; this handler returns it as the body directly so
        clients don't see an extra ``{"detail": ...}`` wrap.
        """
        if isinstance(exc.detail, dict) and "error" in exc.detail:
            return JSONResponse(status_code=exc.status_code, content=exc.detail)
        return JSONResponse(
            status_code=exc.status_code,
            content=build_error(
                exc.status_code, "ERROR", str(exc.detail)
            ),
        )

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all: log and return a generic 500.

        Adapter and driver outages, including datastore connectivity, must
        surface as a logged 5xx instead of being masked as 404 or an empty
        result. The message is withheld from the client because driver errors
        can carry host names and query fragments. Never log request bodies or
        headers here.
        """
        logger.error(
            "Unhandled %s on %s %s",
            type(exc).__name__,
            request.method,
            request.url.path,
            exc_info=exc,
        )
        return JSONResponse(
            status_code=500,
            content=build_error(500, "INTERNAL", "Internal error."),
        )
