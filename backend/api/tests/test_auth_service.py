"""Unit tests for ``AuthService`` (orchestration of all 6 auth flows).

Strict-TDD, high-fidelity: the service is wired with REAL collaborators —
``RedisOtpStore`` over ``fakeredis``, ``JwtTokenService`` with a test secret,
``RefreshSessionStore`` over ``mongomock`` — plus a ``FakeEmailSender`` and
dict-backed fake user/participant repos. Assertions exercise real behaviour
(decode the minted JWT, query the refresh-session collection) rather than
mock call-counts.

The ONLY place a test reads the OTP code is ``fake_email.last_code(email)`` —
mirroring production where the code never escapes except via the email body.
"""

from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any, Callable

import fakeredis
import mongomock
import pytest

from openwellness_core.adapters.mongo.repositories.mongo_refresh_session_repository import (
    MongoRefreshSessionRepository,
)
from openwellness_core.application.exceptions import LimitExceededException
from openwellness_core.domain.models.user import User

from openwellness_api.auth import errors
from openwellness_api.auth.email_sender import FakeEmailSender
from openwellness_api.auth.otp_store import RedisOtpStore
from openwellness_api.auth.service import (
    AuthService,
    Credential,
    RefreshedCredential,
    SendOutcome,
)
from openwellness_api.auth.session_store import RefreshSessionStore
from openwellness_api.auth.token_service import JwtTokenService
from openwellness_api.config import AuthSettings


FIXED_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

VERIFIED_EMAIL = "alice@example.com"
VERIFIED_USER_ID = "user-verified-1"
VERIFIED_PID = "PID-100"

UNVERIFIED_EMAIL = "bob@example.com"
UNVERIFIED_USER_ID = "user-unverified-1"
UNVERIFIED_PARTICIPANT_ID = "participant-doc-1"
UNVERIFIED_PID = "PID-200"


# --------------------------------------------------------------------------- #
# Fakes: repos + scheduler
# --------------------------------------------------------------------------- #
class FakeUserRepo:
    """Minimal in-memory user repo: get_by_id / get_by_email / save."""

    def __init__(self) -> None:
        self._by_id: dict[str, User] = {}

    def add(self, user: User) -> None:
        self._by_id[user.id] = user

    def get_by_id(self, entity_id: str) -> User | None:
        return self._by_id.get(entity_id)

    def get_by_email(self, email: str) -> list[User]:
        return [u for u in self._by_id.values() if u.email == email]

    def save(self, user: User) -> User:
        self._by_id[user.id] = user
        return user


class _FakeParticipant:
    """Stand-in participant: only the attributes the service reads."""

    def __init__(self, *, id: str, user_id: str | None) -> None:
        self.id = id
        self.user_id = user_id


class FakeParticipantRepo:
    def __init__(self) -> None:
        self._by_id: dict[str, _FakeParticipant] = {}

    def add(self, participant: _FakeParticipant) -> None:
        self._by_id[participant.id] = participant

    def get_by_id(self, entity_id: str) -> _FakeParticipant | None:
        return self._by_id.get(entity_id)


class RecordingScheduler:
    """Captures ``add_task`` calls without running them (until invoked)."""

    def __init__(self) -> None:
        self.tasks: list[tuple[Callable[..., Any], tuple, dict]] = []

    def add_task(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None:
        self.tasks.append((func, args, kwargs))

    def run_all(self) -> None:
        for func, args, kwargs in self.tasks:
            func(*args, **kwargs)


# --------------------------------------------------------------------------- #
# Builders
# --------------------------------------------------------------------------- #
def _settings(**overrides: object) -> AuthSettings:
    base: dict[str, object] = {
        "jwt_secret": "x" * 32,
        "code_pepper": "test-pepper",
        "otp_ttl_seconds": 600,
        "otp_length": 6,
        "otp_max_attempts": 5,
        "refresh_ttl_seconds": 2592000,
        "send_window_seconds": 3600,
        "send_max_per_window": 5,
        "resend_cooldown_seconds": 60,
        "ip_window_seconds": 3600,
        "ip_max_per_window": 20,
    }
    base.update(overrides)
    return AuthSettings(**base)  # type: ignore[arg-type]


def _verified_user() -> User:
    return User(
        id=VERIFIED_USER_ID,
        email=VERIFIED_EMAIL,
        is_active=True,
        username="alice",
        roles={"participant": {"pid": VERIFIED_PID}},
        verified_id="already-verified-marker",
        registered_at=FIXED_NOW,
    )


def _unverified_user() -> User:
    return User(
        id=UNVERIFIED_USER_ID,
        email=UNVERIFIED_EMAIL,
        is_active=False,
        username="bob",
        roles={"participant": {"pid": UNVERIFIED_PID}},
        verified_id=None,
        registered_at=None,
    )


class _Ctx:
    """Bundle of the service + its collaborators for assertions."""

    def __init__(self, **overrides: object) -> None:
        self.settings = _settings(**overrides)
        # PyJWT validates ``exp`` against real wall-clock time, so the clock
        # must track real "now" for a freshly minted access token to verify.
        # A single shared clock keeps the OTP store, session store, and token
        # service consistent within a test run.
        self.now = datetime.now(timezone.utc)
        self.clock: Callable[[], datetime] = lambda: self.now
        self.redis = fakeredis.FakeRedis(decode_responses=True)
        self.otp_store = RedisOtpStore(
            redis=self.redis, settings=self.settings, clock=self.clock
        )
        self.token_service = JwtTokenService(
            settings=self.settings, clock=self.clock
        )
        self.collection: Any = mongomock.MongoClient()["testdb"][
            "auth_refresh_sessions"
        ]
        adapter = MongoRefreshSessionRepository(collection=self.collection)
        adapter.ensure_indexes()
        self.session_store = RefreshSessionStore(repo=adapter, clock=self.clock)
        self.email = FakeEmailSender()
        self.user_repo = FakeUserRepo()
        self.participant_repo = FakeParticipantRepo()

        # Seed a pre-provisioned, verified participant-user (login) and an
        # unverified pre-provisioned participant-user (registration).
        self.user_repo.add(_verified_user())
        self.user_repo.add(_unverified_user())
        self.participant_repo.add(
            _FakeParticipant(
                id=UNVERIFIED_PARTICIPANT_ID, user_id=UNVERIFIED_USER_ID
            )
        )

        self.service = AuthService(
            settings=self.settings,
            otp_store=self.otp_store,
            token_service=self.token_service,
            session_store=self.session_store,
            email_sender=self.email,
            user_repo=self.user_repo,
            participant_repo=self.participant_repo,
            clock=self.clock,
        )

    def session_doc(self, raw_refresh: str) -> dict | None:
        token_hash = self.token_service.hash_refresh(raw_refresh)
        return self.collection.find_one({"tokenHash": token_hash})


@pytest.fixture
def ctx() -> _Ctx:
    return _Ctx()


# --------------------------------------------------------------------------- #
# Login happy path
# --------------------------------------------------------------------------- #
def test_login_happy_path(ctx: _Ctx) -> None:
    outcome = ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="1.2.3.4")
    assert isinstance(outcome, SendOutcome)
    assert outcome.expires_in_seconds == ctx.settings.otp_ttl_seconds
    assert outcome.resend_after_seconds == ctx.settings.resend_cooldown_seconds
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE

    code = ctx.email.last_code(VERIFIED_EMAIL)
    assert code is not None and len(code) == ctx.settings.otp_length

    cred = ctx.service.verify_login_code(
        email=VERIFIED_EMAIL, code=code, user_agent="UA/1", ip="1.2.3.4"
    )
    assert isinstance(cred, Credential)
    assert cred.token_type == "Bearer"
    assert cred.expires_in_seconds == ctx.settings.access_ttl_seconds
    assert cred.user_id == VERIFIED_USER_ID
    assert cred.participant == f"participants/{VERIFIED_PID}"

    # Real JWT decode through the token service.
    claims = ctx.token_service.verify_access(cred.access_token)
    assert claims.sub == VERIFIED_USER_ID
    assert claims.participant == VERIFIED_PID
    assert "participant" in claims.roles

    # A refresh-session row exists for the raw token's hash.
    doc = ctx.session_doc(cred.refresh_token)
    assert doc is not None
    assert doc["userId"] == VERIFIED_USER_ID
    assert doc["revoked"] is False
    assert doc["rotatedAt"] is None


def test_login_email_is_normalized(ctx: _Ctx) -> None:
    # Mixed-case / whitespace email must reach the verified account.
    outcome = ctx.service.send_login_code(
        email="  Alice@Example.COM  ", ip="1.2.3.4"
    )
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    code = ctx.email.last_code(VERIFIED_EMAIL)
    assert code is not None
    cred = ctx.service.verify_login_code(email="ALICE@example.com", code=code)
    assert cred.user_id == VERIFIED_USER_ID


# --------------------------------------------------------------------------- #
# Registration happy path
# --------------------------------------------------------------------------- #
def test_registration_happy_path(ctx: _Ctx) -> None:
    outcome = ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="1.2.3.4",
    )
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE

    code = ctx.email.last_code(UNVERIFIED_EMAIL)
    assert code is not None

    cred = ctx.service.verify_registration_code(
        email=UNVERIFIED_EMAIL, code=code
    )
    assert isinstance(cred, Credential)
    assert cred.user_id == UNVERIFIED_USER_ID

    user = ctx.user_repo.get_by_id(UNVERIFIED_USER_ID)
    assert user is not None
    assert user.verified_id  # now truthy
    assert user.registered_at == ctx.now
    assert user.email == UNVERIFIED_EMAIL
    assert user.is_active is True

    # Credential carries a valid access JWT + a persisted refresh session.
    claims = ctx.token_service.verify_access(cred.access_token)
    assert claims.sub == UNVERIFIED_USER_ID
    assert ctx.session_doc(cred.refresh_token) is not None


def test_registration_strips_participants_prefix(ctx: _Ctx) -> None:
    outcome = ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=f"participants/{UNVERIFIED_PARTICIPANT_ID}",
        ip="1.2.3.4",
    )
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    assert ctx.email.last_code(UNVERIFIED_EMAIL) is not None


# --------------------------------------------------------------------------- #
# Anti-enumeration (send)
# --------------------------------------------------------------------------- #
def test_send_login_unknown_email_uniform_and_silent(ctx: _Ctx) -> None:
    happy = ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="9.9.9.9")
    unknown = ctx.service.send_login_code(
        email="nobody@example.com", ip="9.9.9.8"
    )
    # Identical outcome fields (no leak of existence).
    assert unknown == happy
    # Nothing sent for the unknown address.
    assert ctx.email.last_code("nobody@example.com") is None
    assert all(e != "nobody@example.com" for e, _, _ in ctx.email.sent)


def test_send_login_inactive_user_silent(ctx: _Ctx) -> None:
    # Deactivate the verified user; eligibility must now fail silently.
    user = ctx.user_repo.get_by_id(VERIFIED_USER_ID)
    assert user is not None
    ctx.user_repo.save(replace(user, is_active=False))

    outcome = ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="9.9.9.9")
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    assert ctx.email.last_code(VERIFIED_EMAIL) is None


def test_send_login_multiple_users_silent_and_warns(
    ctx: _Ctx, caplog: pytest.LogCaptureFixture
) -> None:
    # Two users share the same email → ineligible (ambiguous).
    dup = replace(_verified_user(), id="user-dup")
    ctx.user_repo.add(dup)

    with caplog.at_level(logging.WARNING):
        outcome = ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="9.9.9.9")

    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    assert ctx.email.last_code(VERIFIED_EMAIL) is None
    # The alert uses the sha256 of the email, never the raw email.
    joined = " ".join(r.getMessage() for r in caplog.records)
    assert "email_sha256" in joined
    assert VERIFIED_EMAIL not in joined


def test_send_registration_unknown_participant_silent(ctx: _Ctx) -> None:
    outcome = ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL, participant_id="no-such", ip="9.9.9.9"
    )
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    assert ctx.email.last_code(UNVERIFIED_EMAIL) is None


def test_send_registration_already_verified_user_silent(ctx: _Ctx) -> None:
    # Mark the participant's user already verified → not eligible to register.
    user = ctx.user_repo.get_by_id(UNVERIFIED_USER_ID)
    assert user is not None
    ctx.user_repo.save(replace(user, verified_id="already"))

    outcome = ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="9.9.9.9",
    )
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    assert ctx.email.last_code(UNVERIFIED_EMAIL) is None


def test_send_registration_email_owned_by_other_verified_user_silent(
    ctx: _Ctx,
) -> None:
    # A DIFFERENT already-verified user owns the target email.
    other = replace(
        _verified_user(), id="other-verified", email=UNVERIFIED_EMAIL
    )
    ctx.user_repo.add(other)

    outcome = ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="9.9.9.9",
    )
    assert outcome.message == errors.UNIFORM_SEND_MESSAGE
    assert ctx.email.last_code(UNVERIFIED_EMAIL) is None


# --------------------------------------------------------------------------- #
# Anti-enumeration (verify): identical 400 regardless of reason
# --------------------------------------------------------------------------- #
def _http_status_detail(exc_info: pytest.ExceptionInfo) -> tuple[int, str]:
    exc = exc_info.value
    status = exc.status_code  # type: ignore[attr-defined]
    detail = exc.detail  # type: ignore[attr-defined]
    return status, detail["error"]["message"]


def test_verify_wrong_code_uniform_400(ctx: _Ctx) -> None:
    ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="1.2.3.4")
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        ctx.service.verify_login_code(email=VERIFIED_EMAIL, code="000000")
    status, message = _http_status_detail(ei)
    assert status == 400

    # Unknown email verify → SAME 400 message (no leak).
    with pytest.raises(HTTPException) as ei2:
        ctx.service.verify_login_code(email="nobody@example.com", code="000000")
    status2, message2 = _http_status_detail(ei2)
    assert status2 == 400
    assert message == message2


def test_verify_registration_wrong_code_uniform_400(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="1.2.3.4",
    )
    with pytest.raises(HTTPException) as ei:
        ctx.service.verify_registration_code(
            email=UNVERIFIED_EMAIL, code="000000"
        )
    status, _ = _http_status_detail(ei)
    assert status == 400


# --------------------------------------------------------------------------- #
# Single-use
# --------------------------------------------------------------------------- #
def test_login_code_single_use(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="1.2.3.4")
    code = ctx.email.last_code(VERIFIED_EMAIL)
    assert code is not None

    ctx.service.verify_login_code(email=VERIFIED_EMAIL, code=code)
    with pytest.raises(HTTPException) as ei:
        ctx.service.verify_login_code(email=VERIFIED_EMAIL, code=code)
    status, _ = _http_status_detail(ei)
    assert status == 400


# --------------------------------------------------------------------------- #
# Lockout propagates 429 (LimitExceededException, NOT converted to 400)
# --------------------------------------------------------------------------- #
def test_lockout_propagates_uncaught(ctx: _Ctx) -> None:
    ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="1.2.3.4")
    # Exhaust attempts with wrong codes; the final attempt locks out.
    for _ in range(ctx.settings.otp_max_attempts - 1):
        try:
            ctx.service.verify_login_code(email=VERIFIED_EMAIL, code="000000")
        except Exception:
            pass
    with pytest.raises(LimitExceededException):
        ctx.service.verify_login_code(email=VERIFIED_EMAIL, code="000000")


# --------------------------------------------------------------------------- #
# Refresh rotation + reuse
# --------------------------------------------------------------------------- #
def _issue_login(ctx: _Ctx) -> Credential:
    ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="1.2.3.4")
    code = ctx.email.last_code(VERIFIED_EMAIL)
    assert code is not None
    return ctx.service.verify_login_code(email=VERIFIED_EMAIL, code=code)


def test_refresh_rotation_and_reuse_revokes_family(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    cred = _issue_login(ctx)
    old_raw = cred.refresh_token

    rotated = ctx.service.refresh_token(raw_refresh=old_raw)
    assert isinstance(rotated, RefreshedCredential)
    assert rotated.refresh_token != old_raw
    assert rotated.token_type == "Bearer"
    new_claims = ctx.token_service.verify_access(rotated.access_token)
    assert new_claims.sub == VERIFIED_USER_ID

    # Replaying the OLD token → 401 AND it revokes the family.
    with pytest.raises(HTTPException) as ei:
        ctx.service.refresh_token(raw_refresh=old_raw)
    assert ei.value.status_code == 401  # type: ignore[attr-defined]

    # The NEW token now also fails (family revoked by reuse detection).
    with pytest.raises(HTTPException) as ei2:
        ctx.service.refresh_token(raw_refresh=rotated.refresh_token)
    assert ei2.value.status_code == 401  # type: ignore[attr-defined]


def test_refresh_unknown_token_401(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        ctx.service.refresh_token(raw_refresh="garbage-token")
    assert ei.value.status_code == 401  # type: ignore[attr-defined]
    assert ei.value.detail["error"]["status"] == "UNAUTHENTICATED"  # type: ignore[attr-defined]


def test_refresh_inactive_user_401(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    cred = _issue_login(ctx)
    user = ctx.user_repo.get_by_id(VERIFIED_USER_ID)
    assert user is not None
    ctx.user_repo.save(replace(user, is_active=False))

    with pytest.raises(HTTPException) as ei:
        ctx.service.refresh_token(raw_refresh=cred.refresh_token)
    assert ei.value.status_code == 401  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# Revoke
# --------------------------------------------------------------------------- #
def test_revoke_refresh_then_refresh_401(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    cred = _issue_login(ctx)
    ctx.service.revoke_refresh(raw_refresh=cred.refresh_token)
    with pytest.raises(HTTPException) as ei:
        ctx.service.refresh_token(raw_refresh=cred.refresh_token)
    assert ei.value.status_code == 401  # type: ignore[attr-defined]


def test_revoke_refresh_unknown_is_idempotent(ctx: _Ctx) -> None:
    # Must not raise on an unknown token.
    ctx.service.revoke_refresh(raw_refresh="never-issued")


def test_revoke_all_for_access_revokes_sessions(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    cred = _issue_login(ctx)
    ctx.service.revoke_all_for_access(access_token=cred.access_token)
    with pytest.raises(HTTPException) as ei:
        ctx.service.refresh_token(raw_refresh=cred.refresh_token)
    assert ei.value.status_code == 401  # type: ignore[attr-defined]


def test_revoke_all_for_access_invalid_token_401(ctx: _Ctx) -> None:
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as ei:
        ctx.service.revoke_all_for_access(access_token="not.a.jwt")
    assert ei.value.status_code == 401  # type: ignore[attr-defined]


# --------------------------------------------------------------------------- #
# No code / raw email in logs
# --------------------------------------------------------------------------- #
def test_no_code_or_email_in_logs(
    ctx: _Ctx, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.DEBUG):
        ctx.service.send_login_code(email=VERIFIED_EMAIL, ip="1.2.3.4")
        code = ctx.email.last_code(VERIFIED_EMAIL)
        assert code is not None
        ctx.service.verify_login_code(email=VERIFIED_EMAIL, code=code)

    blob = "\n".join(r.getMessage() for r in caplog.records)
    assert code not in blob
    assert VERIFIED_EMAIL not in blob


# --------------------------------------------------------------------------- #
# Background scheduling
# --------------------------------------------------------------------------- #
def test_send_login_schedules_email_when_tasks_given(ctx: _Ctx) -> None:
    scheduler = RecordingScheduler()
    ctx.service.send_login_code(
        email=VERIFIED_EMAIL, ip="1.2.3.4", tasks=scheduler
    )
    # Email was queued, not sent synchronously.
    assert ctx.email.sent == []
    assert len(scheduler.tasks) == 1
    func, _, kwargs = scheduler.tasks[0]
    assert func == ctx.email.send_otp
    assert kwargs["email"] == VERIFIED_EMAIL
    assert kwargs["purpose"] == "login"

    # Running the queued task records the send.
    scheduler.run_all()
    assert ctx.email.last_code(VERIFIED_EMAIL) is not None


def test_send_registration_schedules_email_when_tasks_given(ctx: _Ctx) -> None:
    scheduler = RecordingScheduler()
    ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="1.2.3.4",
        tasks=scheduler,
    )
    assert ctx.email.sent == []
    assert len(scheduler.tasks) == 1
    _, _, kwargs = scheduler.tasks[0]
    assert kwargs["purpose"] == "registration"
    scheduler.run_all()
    assert ctx.email.last_code(UNVERIFIED_EMAIL) is not None


# --------------------------------------------------------------------------- #
# Fix I-2 — registration verify save collision is a uniform 400 (not a 500)
# --------------------------------------------------------------------------- #
def test_registration_email_collision_is_uniform_400(ctx: _Ctx) -> None:
    """A UNIQUE-email collision on ``save`` must surface as the uniform 400.

    The real user collection has a unique email index; if a DIFFERENT
    unverified user already holds the normalized email, ``save`` raises
    ``DuplicateEntityException``. That must be caught and re-raised as
    ``errors.invalid_code()`` (status 400, generic message) rather than
    escaping as an unhandled 500 (which would also leak a distinguishable
    response shape).
    """
    from fastapi import HTTPException
    from openwellness_core.application.exceptions import DuplicateEntityException

    # Drive a real, valid registration verify (real OTP from the email).
    ctx.service.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="1.2.3.4",
    )
    code = ctx.email.last_code(UNVERIFIED_EMAIL)
    assert code is not None

    # The save() now collides on the unique email index.
    def _raise_dup(_user: User) -> User:
        raise DuplicateEntityException("dup")

    ctx.user_repo.save = _raise_dup  # type: ignore[method-assign]

    with pytest.raises(HTTPException) as ei:
        ctx.service.verify_registration_code(email=UNVERIFIED_EMAIL, code=code)

    status, message = _http_status_detail(ei)
    assert status == 400
    # Same generic, reason-free message as every other verify failure.
    expected = errors.invalid_code().detail["error"]["message"]  # type: ignore[index]
    assert message == expected


# --------------------------------------------------------------------------- #
# Fix I-1 — registration send issues a CONSTANT query shape (timing oracle)
# --------------------------------------------------------------------------- #
class _CountingUserRepo:
    """Wrap a real user repo, recording every get_by_id/get_by_email call."""

    def __init__(self, inner: FakeUserRepo) -> None:
        self._inner = inner
        self.calls: list[tuple[str, Any]] = []

    def get_by_id(self, entity_id: str) -> User | None:
        self.calls.append(("get_by_id", entity_id))
        return self._inner.get_by_id(entity_id)

    def get_by_email(self, email: str) -> list[User]:
        self.calls.append(("get_by_email", email))
        return self._inner.get_by_email(email)

    def save(self, user: User) -> User:
        return self._inner.save(user)


class _CountingParticipantRepo:
    """Wrap a real participant repo, recording every get_by_id call."""

    def __init__(self, inner: FakeParticipantRepo) -> None:
        self._inner = inner
        self.calls: list[tuple[str, Any]] = []

    def get_by_id(self, entity_id: str) -> _FakeParticipant | None:
        self.calls.append(("get_by_id", entity_id))
        return self._inner.get_by_id(entity_id)


def _counted_service(ctx: _Ctx) -> tuple[AuthService, _CountingUserRepo, _CountingParticipantRepo]:
    """A fresh AuthService over the ctx's collaborators, with COUNTING repos."""
    user_repo = _CountingUserRepo(ctx.user_repo)
    participant_repo = _CountingParticipantRepo(ctx.participant_repo)
    service = AuthService(
        settings=ctx.settings,
        otp_store=ctx.otp_store,
        token_service=ctx.token_service,
        session_store=ctx.session_store,
        email_sender=ctx.email,
        user_repo=user_repo,
        participant_repo=participant_repo,
        clock=ctx.clock,
    )
    return service, user_repo, participant_repo


def _shape(user_repo: _CountingUserRepo, participant_repo: _CountingParticipantRepo) -> tuple:
    """A comparable signature of repo-call kinds (not their data)."""
    user_kinds = tuple(kind for kind, _ in user_repo.calls)
    participant_kinds = tuple(kind for kind, _ in participant_repo.calls)
    return participant_kinds, user_kinds


def test_registration_send_query_shape_is_constant() -> None:
    """The registration-send DB query shape must NOT vary with eligibility.

    A query-count difference between (eligible / unknown participant /
    already-verified user) is a measurable timing oracle that leaks whether a
    participant id exists, undercutting the uniform-200 guarantee. All three
    paths must issue the identical shape: participant.get_by_id,
    user.get_by_id, user.get_by_email.

    Each case uses its OWN ``_Ctx`` (fresh redis) so the shared send-rate-limit
    counters never interfere with the per-case query-shape measurement.
    """
    # (a) Eligible target.
    ctx_a = _Ctx()
    svc_a, u_a, p_a = _counted_service(ctx_a)
    svc_a.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="1.2.3.4",
    )
    shape_a = _shape(u_a, p_a)

    # (b) Unknown participant.
    ctx_b = _Ctx()
    svc_b, u_b, p_b = _counted_service(ctx_b)
    svc_b.send_registration_code(
        email="someone@example.com",
        participant_id="no-such-participant",
        ip="1.2.3.4",
    )
    shape_b = _shape(u_b, p_b)

    # (c) Already-verified user behind the participant.
    ctx_c = _Ctx()
    user = ctx_c.user_repo.get_by_id(UNVERIFIED_USER_ID)
    assert user is not None
    ctx_c.user_repo.save(replace(user, verified_id="already"))
    svc_c, u_c, p_c = _counted_service(ctx_c)
    svc_c.send_registration_code(
        email=UNVERIFIED_EMAIL,
        participant_id=UNVERIFIED_PARTICIPANT_ID,
        ip="1.2.3.4",
    )
    shape_c = _shape(u_c, p_c)

    # Identical shape across all three eligibility outcomes.
    assert shape_a == shape_b == shape_c
    # Concretely: 1 participant lookup + (1 user get_by_id + 1 user get_by_email).
    assert shape_a == (("get_by_id",), ("get_by_id", "get_by_email"))
