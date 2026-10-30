"""Refresh-token rotation policy over the RefreshSessionRepository port.

``RefreshSessionStore`` owns the rotation and reuse-detection *policy*; the
persistence side lives behind ``RefreshSessionRepository`` (a Mongo adapter
today, Postgres in Phase 4), so the policy is written once. It never imports a
datastore driver.

It does **not** generate refresh tokens or hashes (the caller, via the token
service, mints the raw token and its sha256 hash and passes the *hash* in), mint
access JWTs, send email, or touch Redis/HTTP. Collaborators (the repository
port and a tz-aware ``clock``) are injected; the store has no module-level
singletons and never reads ``os.environ``.

Invariants:

* Single use: ``repo.mark_rotated`` is an atomic compare-and-set, so each
  refresh token is consumed exactly once. A presented token that is already
  rotated/revoked, or that loses the CAS race, is reuse and revokes the whole
  family *before* ``RefreshReuse`` surfaces.
* An unknown or expired token raises ``RefreshInvalid`` and revokes nothing.
* If the child insert fails after a won CAS, the parent is rolled back with
  ``clear_rotated`` so the user can retry with the same token.
* Expiry is re-checked on every consume; the datastore's TTL sweep is
  best-effort only.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from openwellness_core.application.repositories import (
    RefreshSession,
    RefreshSessionRepository,
)


class RefreshInvalid(Exception):
    """Raised when a presented refresh token is unknown or expired.

    There is no family to defend in this case (the token was never a live,
    rotatable session), so nothing is revoked. The caller maps this to a 401.
    """


class RefreshReuse(Exception):
    """Raised when a presented refresh token has already been consumed/revoked.

    Covers an already-rotated or already-revoked token *and* a concurrent
    rotation that lost the CAS race. In every case the store has **already**
    revoked the entire token family (reason ``"reuse_detected"``) before this
    is raised. The caller maps this to a 401.
    """


@dataclass(frozen=True)
class RotationResult:
    """The identity carried forward from a successful rotation."""

    user_id: str
    participant_id: str | None
    family_id: str


class RefreshSessionStore:
    """Refresh-session rotation + reuse detection over the repository port."""

    def __init__(
        self, *, repo: RefreshSessionRepository, clock: Callable[[], datetime]
    ) -> None:
        """Wire the store to its collaborators.

        Contract: the injected ``clock`` MUST return a timezone-aware UTC
        ``datetime`` (naive or non-UTC values break expiry comparison).
        """
        self._repo = repo
        self._clock = clock

    def create(
        self,
        *,
        token_hash: str,
        user_id: str,
        participant_id: str | None,
        family_id: str,
        parent_id: str | None = None,
        expires_at: datetime,
        user_agent: str | None = None,
        ip: str | None = None,
        created_by: str,
    ) -> None:
        """Insert a fresh, live session.

        Used for initial credential issuance (a brand-new family at
        login/registration) and internally as the rotated child insert. A
        ``family_id`` is not generated here: the caller supplies it.
        """
        self._repo.create(
            RefreshSession(
                token_hash=token_hash,
                user_id=user_id,
                participant_id=participant_id,
                family_id=family_id,
                parent_id=parent_id,
                issued_at=self._clock(),
                expires_at=expires_at,
                user_agent=user_agent,
                ip=ip,
                created_by=created_by,
            )
        )

    def consume_for_rotation(
        self,
        *,
        presented_hash: str,
        new_token_hash: str,
        new_expires_at: datetime,
        user_agent: str | None = None,
        ip: str | None = None,
    ) -> RotationResult:
        """Single-use rotate ``presented_hash`` into a fresh child token.

        Raises :class:`RefreshInvalid` for an unknown/expired token (no family
        revoke) and :class:`RefreshReuse` for a reused/already-revoked token or
        a lost CAS race (the whole family is revoked first).
        """
        session = self._repo.get_by_token_hash(presented_hash)
        if session is None:
            # Unknown token: never a live session here, nothing to defend.
            raise RefreshInvalid("refresh token not found")

        # Already consumed or revoked: a live token was presented twice (or
        # after an explicit revoke). Burn the whole family, then signal.
        if session.revoked or session.rotated_at is not None:
            self.revoke_family(session.family_id, reason="reuse_detected")
            raise RefreshReuse("refresh token reuse detected")

        # Expired is invalid, not reuse: it was never rotated, so there is no
        # family to defend.
        if session.expires_at < self._clock():
            raise RefreshInvalid("refresh token expired")

        # Single-use correctness relies on this CAS alone: there is no
        # transaction around it and the child insert (standalone Mongo 4.0).
        now = self._clock()
        if not self._repo.mark_rotated(session.id, rotated_at=now):
            self.revoke_family(session.family_id, reason="reuse_detected")
            raise RefreshReuse("refresh token reuse detected (lost CAS race)")

        # The CAS and the insert are two non-atomic writes; if the insert fails
        # we'd leave a consumed parent with no child, silently logging the user
        # out. Roll the parent back and re-raise so the SAME token can retry.
        try:
            self.create(
                token_hash=new_token_hash,
                user_id=session.user_id,
                participant_id=session.participant_id,
                family_id=session.family_id,
                parent_id=session.id,
                expires_at=new_expires_at,
                user_agent=user_agent,
                ip=ip,
                created_by=session.user_id,
            )
        except Exception:
            # Conditional on the exact value WE set, so a concurrent legitimate
            # re-consume is never clobbered.
            self._repo.clear_rotated(session.id, rotated_at=now)
            raise
        return RotationResult(
            user_id=session.user_id,
            participant_id=session.participant_id,
            family_id=session.family_id,
        )

    def revoke_by_hash(self, token_hash: str, *, reason: str = "logout") -> None:
        """Revoke a single session by token hash; idempotent (a miss is fine)."""
        self._repo.revoke_by_token_hash(
            token_hash, reason=reason, revoked_at=self._clock()
        )

    def revoke_family(self, family_id: str, *, reason: str) -> None:
        """Revoke every session in a token family (reuse detection, explicit kill)."""
        self._repo.revoke_family(
            family_id, reason=reason, revoked_at=self._clock()
        )

    def revoke_all_for_user(
        self, user_id: str, *, reason: str = "logout_all"
    ) -> None:
        """Revoke every session belonging to a user (global sign-out)."""
        self._repo.revoke_all_for_user(
            user_id, reason=reason, revoked_at=self._clock()
        )


__all__ = [
    "RefreshInvalid",
    "RefreshReuse",
    "RefreshSessionStore",
    "RotationResult",
]
