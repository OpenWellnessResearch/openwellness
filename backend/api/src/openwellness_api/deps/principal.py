"""Principal (caller identity) — strict bearer verification.

``get_principal`` is the one place a bearer token is validated. It either
returns a verified :class:`Principal` or raises the 401 AIP-193 envelope; there
is no anonymous or header-supplied identity. Resource routes get it from
``FloorRoute`` (see ``v1.py``) before FastAPI reads the request body, and
handlers may also ``Depends(get_principal)`` to learn who is calling.

A missing auth container is a wiring bug and surfaces as a 500, never as an
anonymous pass.

CIRCULAR-IMPORT NOTE: do NOT import ``auth.errors`` or ``auth.service`` at
module level — that would create a cycle via ``common.handlers``. The 401
envelope is built with the leaf-module ``errors.responses.build_error``, and
``InvalidAccessToken`` is imported inside the function.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, Request

from ..errors.responses import build_error


@dataclass(frozen=True)
class Principal:
    """The verified caller of an API request."""

    id: str
    roles: tuple[str, ...] = ()
    """Roles from the verified access token."""

    participant: str | None = None
    """The bare participant id from the JWT ``participant`` claim, if any."""

    coach_studies: tuple[str, ...] = ()
    """Study ids a coach is assigned to, from the JWT ``coach_studies`` claim."""

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


def _unauthenticated() -> HTTPException:
    # One body for every failure: missing, blank, wrong scheme, bad or expired.
    # No WWW-Authenticate header — the mobile client depends on the current shape.
    return HTTPException(
        status_code=401,
        detail=build_error(401, "UNAUTHENTICATED", "Authentication required."),
    )


def get_principal(request: Request) -> Principal:
    """Verify the bearer token and return its principal, or raise the 401."""
    # Lazy: auth/__init__ -> router -> common.handlers -> this module.
    from ..auth.token_service import InvalidAccessToken

    header = request.headers.get("authorization") or ""
    token = header[7:].strip() if header[:7].lower() == "bearer " else ""
    if not token:
        raise _unauthenticated()
    try:
        claims = request.app.state.auth_container.token_service().verify_access(token)
    except InvalidAccessToken:
        raise _unauthenticated() from None
    return Principal(
        id=claims.sub,
        roles=tuple(claims.roles),
        participant=claims.participant,
        coach_studies=tuple(claims.coach_studies),
    )
