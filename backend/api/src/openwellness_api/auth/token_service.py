"""Stateless token primitives for email-OTP auth.

``JwtTokenService`` mints/verifies short-lived HS256 access JWTs and issues
opaque CSPRNG refresh tokens (stored only as SHA-256 hashes). It owns *only*
token crypto — no Redis, Mongo, HTTP, or email concerns live here.

Collaborators (settings + clock) are injected so the service has no global
state and never reads ``os.environ`` directly.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Callable, Sequence

import jwt

from openwellness_api.config import AuthSettings


class InvalidAccessToken(Exception):
    """Raised for any access-token validation failure.

    Wraps the underlying ``jwt.PyJWTError`` (or signals a wrong ``typ``) so
    callers only ever need to catch this single type — raw PyJWT exceptions
    never leak out of :class:`JwtTokenService`.
    """


@dataclass(frozen=True)
class AccessClaims:
    """Validated, read-only view of an access token's claims."""

    sub: str
    participant: str | None
    roles: tuple[str, ...]
    jti: str
    iss: str
    aud: str
    coach_studies: tuple[str, ...] = ()


class JwtTokenService:
    """Mint/verify HS256 access JWTs and issue opaque refresh tokens."""

    def __init__(
        self, *, settings: AuthSettings, clock: Callable[[], datetime]
    ) -> None:
        self._settings = settings
        self._clock = clock

    @property
    def access_ttl_seconds(self) -> int:
        """Access-token lifetime, so callers can report ``expiresInSeconds``."""
        return self._settings.access_ttl_seconds

    def mint_access(
        self,
        *,
        user_id: str,
        participant: str | None = None,
        roles: Sequence[str] = (),
        coach_studies: Sequence[str] = (),
    ) -> str:
        """Encode a signed HS256 access JWT for ``user_id``."""
        now = self._clock()
        exp = now + timedelta(seconds=self._settings.access_ttl_seconds)
        claims: dict[str, object] = {
            "iss": self._settings.jwt_issuer,
            "sub": user_id,
            "aud": self._settings.jwt_audience,
            "iat": now,
            "exp": exp,
            "jti": uuid.uuid4().hex,
            "typ": "access",
            "participant": participant,
            "roles": list(roles),
            "coach_studies": list(coach_studies),
        }
        return jwt.encode(
            claims, self._settings.jwt_secret, algorithm=self._settings.jwt_alg
        )

    def verify_access(self, token: str) -> AccessClaims:
        """Validate signature/issuer/audience/expiry/``typ`` and return claims.

        Raises :class:`InvalidAccessToken` on any failure.
        """
        try:
            payload = jwt.decode(
                token,
                self._settings.jwt_secret,
                algorithms=[self._settings.jwt_alg],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                leeway=self._settings.jwt_leeway_seconds,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidAccessToken("access token validation failed") from exc

        if payload.get("typ") != "access":
            raise InvalidAccessToken(
                f"unexpected token typ: {payload.get('typ')!r}"
            )

        # Validate claim shapes before constructing AccessClaims: a string roles
        # claim must not silently explode into per-character roles, and a
        # non-iterable roles claim must not let a raw TypeError escape the
        # single-exception (InvalidAccessToken) contract.
        raw_roles = payload.get("roles", ())
        if not isinstance(raw_roles, (list, tuple)):
            raise InvalidAccessToken("malformed roles claim")
        roles = tuple(str(r) for r in raw_roles)

        participant = payload.get("participant")
        if participant is not None and not isinstance(participant, str):
            raise InvalidAccessToken("malformed participant claim")

        raw_studies = payload.get("coach_studies", ())
        if not isinstance(raw_studies, (list, tuple)) or not all(
            isinstance(s, str) for s in raw_studies
        ):
            raise InvalidAccessToken("malformed coach_studies claim")

        return AccessClaims(
            sub=str(payload["sub"]),
            participant=participant,
            roles=roles,
            jti=str(payload.get("jti", "")),
            iss=str(payload["iss"]),
            aud=str(payload["aud"]),
            coach_studies=tuple(raw_studies),
        )

    def new_refresh(self) -> str:
        """Return a URL-safe opaque refresh token with 256 bits of entropy."""
        return secrets.token_urlsafe(32)

    def hash_refresh(self, raw: str) -> str:
        """Return the SHA-256 hex digest used to store/look up refresh tokens."""
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()
