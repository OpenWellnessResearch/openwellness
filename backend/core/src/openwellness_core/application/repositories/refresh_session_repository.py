"""RefreshSessionRepository port and its RefreshSession record.

Refresh-session persistence for the API's rotation policy. The port is
datastore-neutral: a Mongo adapter ships today and a Postgres adapter follows
in Phase 4, so the security policy is written once against this contract.

``RefreshSession`` lives here, not in ``domain/models``: it is an auth
persistence record with no business behavior, and keeping it beside the port
means an adapter author imports one module.

The port takes sha256 token hashes only. A raw refresh token never crosses it,
and ``RefreshSession`` has no field that could hold one.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, kw_only=True)
class RefreshSession:
    """One issued refresh token, keyed by the sha256 of the token. All datetimes are tz-aware UTC."""

    token_hash: str
    user_id: str
    participant_id: str | None
    family_id: str
    parent_id: str | None = None
    issued_at: datetime
    expires_at: datetime
    rotated_at: datetime | None = None
    revoked: bool = False
    revoked_at: datetime | None = None
    revoked_reason: str | None = None
    user_agent: str | None = None
    ip: str | None = None
    created_by: str
    id: str = ""  # assigned by the datastore on insert


class RefreshSessionRepository(ABC):
    """Persistence contract for refresh sessions.

    Single-use rotation correctness relies on ``mark_rotated`` alone: there is
    no transaction around it and the child insert, so adapters must make it a
    true atomic compare-and-set.
    """

    @abstractmethod
    def create(self, session: RefreshSession) -> None:
        """Insert ``session``; the datastore assigns its id."""

    @abstractmethod
    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        """Return the session stored under this sha256 hash, or None."""

    @abstractmethod
    def mark_rotated(self, session_id: str, *, rotated_at: datetime) -> bool:
        """Atomic compare-and-set of ``rotated_at``.

        True only if this call changed an unrotated, unrevoked session. False
        for an already-rotated or revoked session and for an id naming nothing.
        """

    @abstractmethod
    def clear_rotated(self, session_id: str, *, rotated_at: datetime) -> None:
        """Undo a rotation, but only while ``rotated_at`` still equals the given value."""

    @abstractmethod
    def revoke_by_token_hash(
        self, token_hash: str, *, reason: str, revoked_at: datetime
    ) -> None:
        """Revoke one session; a miss is not an error (idempotent logout)."""

    @abstractmethod
    def revoke_family(
        self, family_id: str, *, reason: str, revoked_at: datetime
    ) -> None:
        """Revoke every session in a token family, and only that family."""

    @abstractmethod
    def revoke_all_for_user(
        self, user_id: str, *, reason: str, revoked_at: datetime
    ) -> None:
        """Revoke every session of a user, and only that user."""
