"""``AuthService`` — orchestration for all six email-OTP auth flows.

This is the security crux of the feature: it is the ONLY place flow logic
lives, wiring together the already-built collaborators (OTP store, token
service, refresh-session store, email sender, user/participant repos). It is
fully unit-testable without HTTP — it raises ``HTTPException`` (the anti-
enumeration helpers in ``errors.py``) and lets ``LimitExceededException``
propagate uncaught (a global handler maps that to 429 + ``Retry-After``).

Collaborators are injected; the service reads no globals and never touches
``os.environ``. Three security invariants are non-negotiable:

1. Anti-enumeration. Every send returns the SAME 200 (``SendOutcome``),
   eligible or not; every verify failure returns the SAME 400
   (``errors.invalid_code()``); the no-account send path performs a dummy
   HMAC so it takes comparable time to the real path (anti-timing).
2. Controlled ``purpose``. Only the literals ``"login"`` / ``"registration"``
   are ever passed to the OTP store — never a client-supplied value.
3. The OTP code is never logged or returned; it escapes ONLY inside the email
   body, delivered via the email sender. Constant-time/hashed comparisons live
   in the collaborators — no plaintext comparison is reintroduced here.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Callable, Protocol

from pymongo.errors import DuplicateKeyError

from openwellness_api.auth import errors
from openwellness_api.auth.email_sender import EmailSender
from openwellness_api.auth.otp_store import InvalidOtp
from openwellness_api.auth.session_store import RefreshInvalid, RefreshReuse
from openwellness_api.auth.token_service import InvalidAccessToken
from openwellness_api.config import AuthSettings

logger = logging.getLogger(__name__)

# The ONLY purposes ever passed to the OTP store. Keeping these as module
# constants (never a client value) is the boundary that keeps `purpose`
# controlled — a request can never inject an arbitrary namespace.
PURPOSE_LOGIN = "login"
PURPOSE_REGISTRATION = "registration"


# --------------------------------------------------------------------------- #
# Result dataclasses (frozen — pure value carriers across the HTTP boundary)
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class SendOutcome:
    """Uniform send result. Identical regardless of eligibility."""

    expires_in_seconds: int
    resend_after_seconds: int
    message: str


@dataclass(frozen=True)
class Credential:
    """Full credential issued on a successful login/registration verify.

    ``refresh_token`` is the RAW opaque token — returned exactly once; only its
    sha256 hash is persisted in the session store.
    """

    access_token: str
    token_type: str
    expires_in_seconds: int
    refresh_token: str
    user_id: str
    participant: str | None


@dataclass(frozen=True)
class RefreshedCredential:
    """Result of a refresh rotation (new access + new raw refresh)."""

    access_token: str
    token_type: str
    expires_in_seconds: int
    refresh_token: str


class TaskScheduler(Protocol):
    """Minimal background-task sink (FastAPI ``BackgroundTasks``-compatible).

    Declared as a Protocol so the service can schedule email sending without
    importing FastAPI; ``BackgroundTasks.add_task`` satisfies it structurally.
    """

    def add_task(self, func: Callable[..., Any], /, *args: Any, **kwargs: Any) -> None:
        ...


class AuthService:
    """Orchestrate OTP send/verify, credential issuance, refresh, and revoke."""

    def __init__(
        self,
        *,
        settings: AuthSettings,
        otp_store: Any,
        token_service: Any,
        session_store: Any,
        email_sender: EmailSender,
        user_repo: Any,
        participant_repo: Any,
        clock: Callable[[], datetime],
    ) -> None:
        self._settings = settings
        self._otp_store = otp_store
        self._token_service = token_service
        self._session_store = session_store
        self._email_sender = email_sender
        self._user_repo = user_repo
        self._participant_repo = participant_repo
        self._clock = clock

    # ------------------------------------------------------------------ #
    # Small helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().lower()

    def _generate_code(self) -> str:
        """Zero-padded CSPRNG numeric OTP of ``settings.otp_length`` digits.

        Uses ``secrets`` (a CSPRNG) — NEVER TOTP, never ``random``. The code is
        returned to the caller only to be handed to the OTP store + email; it
        is never logged.
        """
        n = self._settings.otp_length
        return f"{secrets.randbelow(10 ** n):0{n}d}"

    @staticmethod
    def _roles_list(user: Any) -> list[str]:
        """Role *types* present on the user (the keys of the roles dict)."""
        # Treat malformed (non-dict) roles as empty so bad stored data can't
        # raise AttributeError/500 here.
        roles = getattr(user, "roles", None)
        roles = roles if isinstance(roles, dict) else {}
        return list(roles.keys())

    @staticmethod
    def _participant_pid(user: Any) -> str | None:
        """Legacy participant id, confirmed shape ``roles.participant.pid``."""
        # Treat malformed (non-dict) roles as empty so bad stored data can't
        # raise AttributeError/500 here.
        roles = getattr(user, "roles", None)
        roles = roles if isinstance(roles, dict) else {}
        participant_role = roles.get("participant") or {}
        return participant_role.get("pid")

    @staticmethod
    def _participant_resource(pid: str | None) -> str | None:
        """AIP resource name for a participant id, or ``None``."""
        return f"participants/{pid}" if pid else None

    @staticmethod
    def _email_sha256(email: str) -> str:
        """Stable, non-reversible email identifier for internal log alerts."""
        return hashlib.sha256(email.encode("utf-8")).hexdigest()

    def _dummy_hash_work(self) -> None:
        """Burn HMAC work comparable to ``store_otp``'s hashing.

        On the no-account send path we must not store or send, but we must take
        similar time to the eligible path so timing can't reveal account
        existence. We hash a random code with the same primitive the OTP store
        uses (HMAC-SHA256 over salt+code keyed by the pepper) and discard it.
        """
        salt = secrets.token_hex(16)
        code = self._generate_code()
        hmac.new(
            key=self._settings.code_pepper.encode(),
            msg=(salt + code).encode(),
            digestmod=hashlib.sha256,
        ).hexdigest()

    def _verified_marker(self, norm_email: str) -> str:
        """Marker written to ``user.verified_id`` on registration.

        Default: ``sha256(email + code_pepper)``. A legacy
        ``bcrypt(email, legacy_verified_id_salt)`` variant is intentionally NOT
        implemented here (bcrypt is not a dependency); if
        ``settings.legacy_verified_id_salt`` is ever required, swap this body —
        the marker is opaque to the rest of the flow (only truthiness matters).
        """
        return hashlib.sha256(
            (norm_email + self._settings.code_pepper).encode()
        ).hexdigest()

    def _send_email(
        self,
        *,
        tasks: TaskScheduler | None,
        email: str,
        code: str,
        purpose: str,
    ) -> None:
        """Deliver the OTP email, backgrounded if a scheduler is supplied.

        With ``tasks`` the send is queued (the HTTP handler returns before the
        SMTP round-trip); without it the send is synchronous, which lets unit
        tests read ``FakeEmailSender.last_code`` immediately.
        """
        ttl = self._settings.otp_ttl_seconds
        if tasks is not None:
            tasks.add_task(
                self._email_sender.send_otp,
                email=email,
                code=code,
                purpose=purpose,
                ttl_seconds=ttl,
            )
        else:
            self._email_sender.send_otp(
                email=email, code=code, purpose=purpose, ttl_seconds=ttl
            )

    def _uniform_send_outcome(self) -> SendOutcome:
        return SendOutcome(
            expires_in_seconds=self._settings.otp_ttl_seconds,
            resend_after_seconds=self._settings.resend_cooldown_seconds,
            message=errors.UNIFORM_SEND_MESSAGE,
        )

    # ------------------------------------------------------------------ #
    # Flow 1 — send login code
    # ------------------------------------------------------------------ #
    def send_login_code(
        self,
        *,
        email: str,
        ip: str | None,
        tasks: TaskScheduler | None = None,
    ) -> SendOutcome:
        norm = self._normalize_email(email)

        # Rate limits run BEFORE eligibility, for everyone, so the lockout
        # surface is identical for known and unknown emails (and the resulting
        # LimitExceededException propagates → 429).
        self._otp_store.check_send_limits(
            purpose=PURPOSE_LOGIN, email=norm, ip=ip
        )

        users = self._user_repo.get_by_email(norm)
        user = self._eligible_login_user(norm, users)

        if user is not None:
            code = self._generate_code()
            self._otp_store.store_otp(
                purpose=PURPOSE_LOGIN,
                email=norm,
                code=code,
                user_id=user.id,
                participant_id=self._participant_pid(user),
            )
            self._send_email(
                tasks=tasks, email=norm, code=code, purpose=PURPOSE_LOGIN
            )
        else:
            # No store, no send — but match the eligible path's timing.
            self._dummy_hash_work()

        # Same response either way (anti-enumeration).
        return self._uniform_send_outcome()

    def _eligible_login_user(self, norm: str, users: list[Any]) -> Any | None:
        """Return the single eligible login user, else ``None``.

        Eligible iff EXACTLY ONE user owns the email AND that user is active,
        has a truthy ``verified_id`` (already registered), and has a participant
        pid. More than one user for an email is ambiguous → ineligible + an
        internal alert keyed by the email's sha256 (never the raw email).
        """
        if not users:
            return None
        if len(users) > 1:
            logger.warning(
                "multiple users for email_sha256=%s", self._email_sha256(norm)
            )
            return None
        user = users[0]
        if not user.is_active:
            return None
        if not user.verified_id:
            return None
        if not self._participant_pid(user):
            return None
        return user

    # ------------------------------------------------------------------ #
    # Flow 2 — verify login code
    # ------------------------------------------------------------------ #
    def verify_login_code(
        self,
        *,
        email: str,
        code: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> Credential:
        norm = self._normalize_email(email)

        # InvalidOtp → uniform 400. LimitExceededException (lockout) propagates.
        # The OTP-stored participant id is intentionally ignored: the pid is
        # re-derived from the current user below (the source of truth).
        try:
            user_id, _ = self._otp_store.verify_otp(
                purpose=PURPOSE_LOGIN, email=norm, code=code
            )
        except InvalidOtp:
            raise errors.invalid_code()

        # Re-validate against the CURRENT user state (honour deactivation /
        # role changes since the code was issued). Any failure → uniform 400.
        user = self._user_repo.get_by_id(user_id) if user_id else None
        if (
            user is None
            or not user.is_active
            or not user.verified_id
            or not self._participant_pid(user)
        ):
            raise errors.invalid_code()

        # The guard above already rejected a falsy pid, so the participant id is
        # always present here (no fallback to the OTP-stored value needed).
        participant = self._participant_pid(user)
        return self._issue_credential(user, participant, user_agent, ip)

    # ------------------------------------------------------------------ #
    # Flow 3 — send registration code
    # ------------------------------------------------------------------ #
    def send_registration_code(
        self,
        *,
        email: str,
        participant_id: str,
        ip: str | None,
        tasks: TaskScheduler | None = None,
    ) -> SendOutcome:
        norm = self._normalize_email(email)
        # Defensive: accept either a bare pid or a "participants/<id>" name.
        pid = participant_id
        if pid.startswith("participants/"):
            pid = pid[len("participants/") :]

        self._otp_store.check_send_limits(
            purpose=PURPOSE_REGISTRATION, email=norm, ip=ip
        )

        target = self._eligible_registration_target(norm, pid)
        if target is not None:
            user, participant = target
            code = self._generate_code()
            self._otp_store.store_otp(
                purpose=PURPOSE_REGISTRATION,
                email=norm,
                code=code,
                user_id=user.id,
                participant_id=str(participant.id),
            )
            self._send_email(
                tasks=tasks,
                email=norm,
                code=code,
                purpose=PURPOSE_REGISTRATION,
            )
        else:
            self._dummy_hash_work()

        return self._uniform_send_outcome()

    #: Placeholder ObjectId hex used to keep the user ``get_by_id`` round-trip
    #: happening even when there's no real ``participant.user_id`` (a lookup on
    #: a nonexistent id returns None safely). Keeps the query count constant.
    _PLACEHOLDER_USER_ID = "0" * 24

    def _eligible_registration_target(
        self, norm: str, pid: str
    ) -> tuple[Any, Any] | None:
        """Return ``(user, participant)`` eligible to register, else ``None``.

        Eligible iff the participant exists and is linked to a user that has NOT
        yet registered (falsy ``verified_id``), AND no DIFFERENT already-
        verified user owns the target email.

        Timing equalization (anti-enumeration): we ALWAYS run the SAME three
        lookups regardless of eligibility, THEN decide. A short-circuiting check
        would let the DB query count differ by case (unknown participant → 1
        query, already-verified user → 2, eligible → 3); against real Mongo that
        count gap is a measurable timing oracle leaking whether a participant id
        exists. Flattening to a constant 3 queries closes that oracle while
        preserving the exact eligibility semantics.
        """
        # 1) Participant lookup (always).
        participant = self._participant_repo.get_by_id(pid)

        # 2) User lookup (always) — fall back to a placeholder ObjectId so the
        # second round-trip still happens when there's no real user_id.
        user_id = (
            str(participant.user_id)
            if participant is not None and participant.user_id
            else self._PLACEHOLDER_USER_ID
        )
        user = self._user_repo.get_by_id(user_id)

        # 3) Email-ownership query (always).
        owners = self._user_repo.get_by_email(norm)

        # Now decide eligibility from the gathered results.
        if participant is None or not participant.user_id:
            return None
        if user is None or user.verified_id:
            return None
        # Email must not already belong to a DIFFERENT verified account.
        for owner in owners:
            if owner.verified_id and owner.id != user.id:
                return None

        return user, participant

    # ------------------------------------------------------------------ #
    # Flow 4 — verify registration code
    # ------------------------------------------------------------------ #
    def verify_registration_code(
        self,
        *,
        email: str,
        code: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> Credential:
        norm = self._normalize_email(email)

        try:
            user_id, participant_id = self._otp_store.verify_otp(
                purpose=PURPOSE_REGISTRATION, email=norm, code=code
            )
        except InvalidOtp:
            raise errors.invalid_code()

        # Re-check race guards against current state: the user must still exist
        # and still be unregistered (a concurrent registration would have set
        # verified_id); the participant must still exist.
        user = self._user_repo.get_by_id(user_id) if user_id else None
        if user is None or user.verified_id:
            raise errors.invalid_code()
        participant = (
            self._participant_repo.get_by_id(participant_id)
            if participant_id
            else None
        )
        if participant is None:
            raise errors.invalid_code()

        # Register: stamp the verified marker + registration metadata, and set
        # the (normalized) email so subsequent login-by-email resolves to this
        # account. Activate the account.
        user.verified_id = self._verified_marker(norm)
        user.registered_at = self._clock()
        user.email = norm
        # Completing registration intentionally activates the pre-provisioned
        # account (it was provisioned inactive until the email was verified).
        user.is_active = True
        try:
            self._user_repo.save(user)
        except DuplicateKeyError:
            # The user collection has a UNIQUE email index; if a DIFFERENT
            # (unverified) user already holds this email, save collides. Map it
            # to the uniform 400 so the response shape stays indistinguishable
            # from every other verify failure (no 500, no enumeration leak).
            raise errors.invalid_code()

        return self._issue_credential(
            user, str(participant.id), user_agent, ip
        )

    # ------------------------------------------------------------------ #
    # Shared — issue a fresh credential (new family)
    # ------------------------------------------------------------------ #
    def _issue_credential(
        self,
        user: Any,
        participant_id: str | None,
        user_agent: str | None,
        ip: str | None,
    ) -> Credential:
        # Participant representation contract: ``participant_id`` is the BARE
        # pid throughout the internals — the JWT ``participant`` claim (via
        # ``mint_access``) and the stored session ``participantId`` both carry
        # the bare pid. Only the client-facing ``Credential.participant`` is the
        # AIP resource name ``participants/{pid}`` (built by
        # ``_participant_resource`` below).
        access = self._token_service.mint_access(
            user_id=user.id,
            participant=participant_id,
            roles=self._roles_list(user),
        )
        raw_refresh = self._token_service.new_refresh()
        refresh_hash = self._token_service.hash_refresh(raw_refresh)
        family_id = uuid.uuid4().hex
        expires_at = self._clock() + timedelta(
            seconds=self._settings.refresh_ttl_seconds
        )
        self._session_store.create(
            token_hash=refresh_hash,
            user_id=user.id,
            participant_id=participant_id,
            family_id=family_id,
            parent_id=None,
            expires_at=expires_at,
            user_agent=user_agent,
            ip=ip,
            created_by=user.id,
        )
        return Credential(
            access_token=access,
            token_type="Bearer",
            expires_in_seconds=self._token_service.access_ttl_seconds,
            refresh_token=raw_refresh,
            user_id=user.id,
            participant=self._participant_resource(participant_id),
        )

    # ------------------------------------------------------------------ #
    # Flow 5 — refresh (rotate)
    # ------------------------------------------------------------------ #
    def refresh_token(
        self,
        *,
        raw_refresh: str,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> RefreshedCredential:
        presented_hash = self._token_service.hash_refresh(raw_refresh)
        new_raw = self._token_service.new_refresh()
        new_hash = self._token_service.hash_refresh(new_raw)
        new_expires = self._clock() + timedelta(
            seconds=self._settings.refresh_ttl_seconds
        )

        # Both an unknown/expired token and a reused one map to a single 401.
        # On reuse the store has ALREADY revoked the whole family before raising.
        try:
            result = self._session_store.consume_for_rotation(
                presented_hash=presented_hash,
                new_token_hash=new_hash,
                new_expires_at=new_expires,
                user_agent=user_agent,
                ip=ip,
            )
        except (RefreshInvalid, RefreshReuse):
            raise errors.unauthenticated("Invalid refresh token.")

        # Honour revocation / deactivation since the session was minted.
        user = self._user_repo.get_by_id(result.user_id)
        if user is None or not user.is_active:
            raise errors.unauthenticated("Invalid refresh token.")

        participant = result.participant_id or self._participant_pid(user)
        access = self._token_service.mint_access(
            user_id=user.id,
            participant=participant,
            roles=self._roles_list(user),
        )
        return RefreshedCredential(
            access_token=access,
            token_type="Bearer",
            expires_in_seconds=self._token_service.access_ttl_seconds,
            refresh_token=new_raw,
        )

    # ------------------------------------------------------------------ #
    # Flow 6 — revoke
    # ------------------------------------------------------------------ #
    def revoke_refresh(self, *, raw_refresh: str) -> None:
        """Revoke a single refresh session; idempotent (never raises on miss)."""
        self._session_store.revoke_by_hash(
            self._token_service.hash_refresh(raw_refresh)
        )

    def revoke_all_for_access(self, *, access_token: str) -> None:
        """Global sign-out: revoke all of the caller's refresh sessions.

        Requires a valid access token to identify the user; an invalid token
        yields a 401.
        """
        try:
            claims = self._token_service.verify_access(access_token)
        except InvalidAccessToken:
            raise errors.unauthenticated("Invalid access token.")
        self._session_store.revoke_all_for_user(claims.sub)


__all__ = [
    "AuthService",
    "Credential",
    "PURPOSE_LOGIN",
    "PURPOSE_REGISTRATION",
    "RefreshedCredential",
    "SendOutcome",
    "TaskScheduler",
]
