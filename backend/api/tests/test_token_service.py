"""Unit tests for ``JwtTokenService`` (HS256 access + opaque refresh).

Strict-TDD coverage for token minting, verification, ``typ`` enforcement,
signature/issuer/audience/expiry validation, and opaque refresh tokens.
These tests decode real JWTs and assert real exception behaviour — PyJWT is
never mocked.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
import time_machine

from openwellness_api.config import AuthSettings
from openwellness_api.auth.token_service import (
    AccessClaims,
    InvalidAccessToken,
    JwtTokenService,
)


def _settings(**overrides: object) -> AuthSettings:
    base: dict[str, object] = {
        "jwt_secret": "test-secret-please-change",
        "jwt_issuer": "openwellness-api",
        "jwt_audience": "openwellness-api",
        "access_ttl_seconds": 900,
        "jwt_leeway_seconds": 30,
    }
    base.update(overrides)
    return AuthSettings(**base)  # type: ignore[arg-type]


# Shared fixed instant used by tests that travel verification-time to the mint
# instant. PyJWT's ``decode`` checks ``exp`` against the real wall clock, so any
# test that mints and then verifies a still-valid token must pin real-now to the
# mint instant via ``time_machine`` — otherwise the token looks expired.
FIXED_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _service(clock_value: datetime | None = None, **overrides: object) -> JwtTokenService:
    fixed = clock_value or FIXED_NOW
    return JwtTokenService(settings=_settings(**overrides), clock=lambda: fixed)


# --------------------------------------------------------------------------- #
# Round-trip claims
# --------------------------------------------------------------------------- #
def test_round_trip_returns_matching_claims() -> None:
    svc = _service()
    token = svc.mint_access(
        user_id="user-123", participant="participants/abc", roles=["admin", "viewer"]
    )
    with time_machine.travel(FIXED_NOW, tick=False):
        claims = svc.verify_access(token)

    assert isinstance(claims, AccessClaims)
    assert claims.sub == "user-123"
    assert claims.participant == "participants/abc"
    assert claims.roles == ("admin", "viewer")
    assert claims.jti  # non-empty


def test_round_trip_defaults_participant_none_and_roles_empty() -> None:
    svc = _service()
    token = svc.mint_access(user_id="u1")
    with time_machine.travel(FIXED_NOW, tick=False):
        claims = svc.verify_access(token)
    assert claims.participant is None
    assert claims.roles == ()


def test_each_mint_has_unique_jti() -> None:
    svc = _service()
    t1 = svc.mint_access(user_id="u1")
    t2 = svc.mint_access(user_id="u1")
    with time_machine.travel(FIXED_NOW, tick=False):
        a = svc.verify_access(t1)
        b = svc.verify_access(t2)
    assert a.jti != b.jti


# --------------------------------------------------------------------------- #
# typ enforcement
# --------------------------------------------------------------------------- #
def test_non_access_typ_is_rejected() -> None:
    settings = _settings()
    # Forge an otherwise-valid token with the *correct* secret/iss/aud and a
    # live exp, differing only in `typ`. Verify under the mint instant so the
    # rejection is attributable solely to the typ check, not expiry.
    forged = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "sub": "u1",
            "aud": settings.jwt_audience,
            "iat": FIXED_NOW,
            "exp": FIXED_NOW + timedelta(seconds=900),
            "typ": "refresh",
        },
        settings.jwt_secret,
        algorithm=settings.jwt_alg,
    )
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            svc.verify_access(forged)


# --------------------------------------------------------------------------- #
# Malformed claims / algorithm confusion
# --------------------------------------------------------------------------- #
def _forge_access(
    settings: AuthSettings,
    *,
    secret: str | None = None,
    algorithm: str | None = None,
    **claim_overrides: object,
) -> str:
    """Encode a signature-valid ``typ="access"`` token at ``FIXED_NOW``.

    Defaults to the canonical secret/iss/aud and a live exp/iat/sub so the only
    thing under test is whatever ``claim_overrides`` (or ``algorithm``) change.
    """
    claims: dict[str, object] = {
        "iss": settings.jwt_issuer,
        "sub": "u1",
        "aud": settings.jwt_audience,
        "iat": FIXED_NOW,
        "exp": FIXED_NOW + timedelta(seconds=900),
        "typ": "access",
    }
    claims.update(claim_overrides)
    return jwt.encode(
        claims,
        settings.jwt_secret if secret is None else secret,
        algorithm=settings.jwt_alg if algorithm is None else algorithm,
    )


def test_non_iterable_roles_claim_is_rejected() -> None:
    # A signature-valid token whose `roles` claim is a non-iterable int. Without
    # the fix, `tuple(123)` raises a raw TypeError that escapes verify_access,
    # breaking the single-exception contract. Travel to the mint instant so the
    # rejection is attributable to the malformed claim, not expiry.
    settings = _settings()
    forged = _forge_access(settings, roles=123)
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            svc.verify_access(forged)


def test_coach_studies_round_trip() -> None:
    svc = _service()
    token = svc.mint_access(user_id="u1", coach_studies=["s1", "s2"])
    with time_machine.travel(FIXED_NOW, tick=False):
        claims = svc.verify_access(token)
    assert claims.coach_studies == ("s1", "s2")


def test_coach_studies_absent_defaults_empty() -> None:
    settings = _settings()
    forged = _forge_access(settings)
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        assert svc.verify_access(forged).coach_studies == ()


def test_coach_studies_non_list_rejected() -> None:
    settings = _settings()
    forged = _forge_access(settings, coach_studies="study-a")
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            svc.verify_access(forged)


def test_coach_studies_non_string_item_rejected() -> None:
    settings = _settings()
    forged = _forge_access(settings, coach_studies=["ok", 7])
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            svc.verify_access(forged)


def test_string_roles_claim_is_rejected() -> None:
    # `roles="admin"` must not silently explode into ('a','d','m','i','n'); the
    # fix rejects any non-list/tuple roles shape with InvalidAccessToken.
    settings = _settings()
    forged = _forge_access(settings, roles="admin")
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            svc.verify_access(forged)


def test_unsigned_alg_none_token_is_rejected() -> None:
    # Security regression: an `alg=none` (unsigned) token must NEVER be accepted.
    # PyJWT requires an empty key for the "none" algorithm. Travel to the mint
    # instant so the rejection is the missing signature, not expiry.
    settings = _settings()
    unsigned = _forge_access(settings, secret="", algorithm="none")
    svc = JwtTokenService(settings=settings, clock=lambda: FIXED_NOW)
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            svc.verify_access(unsigned)


# --------------------------------------------------------------------------- #
# Signature / issuer / audience
# --------------------------------------------------------------------------- #
def test_bad_signature_is_rejected() -> None:
    minting = _service(jwt_secret="a-different-secret")
    token = minting.mint_access(user_id="u1")
    verifier = _service()  # canonical secret
    # Travel to the mint instant so the failure is the bad signature, not exp.
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            verifier.verify_access(token)


def test_wrong_issuer_is_rejected() -> None:
    minting = _service(jwt_issuer="some-other-issuer")
    token = minting.mint_access(user_id="u1")
    verifier = _service()  # canonical issuer
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            verifier.verify_access(token)


def test_wrong_audience_is_rejected() -> None:
    minting = _service(jwt_audience="some-other-audience")
    token = minting.mint_access(user_id="u1")
    verifier = _service()  # canonical audience
    with time_machine.travel(FIXED_NOW, tick=False):
        with pytest.raises(InvalidAccessToken):
            verifier.verify_access(token)


# --------------------------------------------------------------------------- #
# Expiry
# --------------------------------------------------------------------------- #
def test_expiry_beyond_leeway_is_rejected() -> None:
    # Clock pinned far in the past; exp is hours before real wall-clock now,
    # so PyJWT (using real now) rejects it — no time-machine required.
    past = datetime(2000, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    svc = _service(clock_value=past)
    token = svc.mint_access(user_id="u1")
    with pytest.raises(InvalidAccessToken):
        svc.verify_access(token)


def test_within_leeway_passes() -> None:
    # Mint at a fixed instant, then travel verification-time to just after exp
    # but inside the 30s leeway window. PyJWT's decode uses the real wall clock
    # for exp, so time-machine is the only way to control verification-time.
    mint_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    svc = _service(clock_value=mint_at)
    token = svc.mint_access(user_id="u1")
    exp = mint_at + timedelta(seconds=900)
    # 10s past exp, well under the 30s leeway.
    with time_machine.travel(exp + timedelta(seconds=10), tick=False):
        claims = svc.verify_access(token)
    assert claims.sub == "u1"


# --------------------------------------------------------------------------- #
# Refresh tokens
# --------------------------------------------------------------------------- #
def test_new_refresh_is_urlsafe_and_unique() -> None:
    svc = _service()
    a = svc.new_refresh()
    b = svc.new_refresh()
    assert a != b
    # 32 bytes base64url-encoded is ~43 chars; assert a sane lower bound.
    assert len(a) >= 43
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")
    assert set(a) <= allowed


def test_hash_refresh_is_deterministic_sha256() -> None:
    svc = _service()
    raw = svc.new_refresh()
    h1 = svc.hash_refresh(raw)
    h2 = svc.hash_refresh(raw)
    assert h1 == h2
    assert len(h1) == 64
    assert h1 != raw


def test_hash_refresh_differs_for_different_inputs() -> None:
    svc = _service()
    assert svc.hash_refresh("token-a") != svc.hash_refresh("token-b")


# --------------------------------------------------------------------------- #
# Misc
# --------------------------------------------------------------------------- #
def test_access_ttl_seconds_is_exposed() -> None:
    svc = _service()
    assert svc.access_ttl_seconds == 900
