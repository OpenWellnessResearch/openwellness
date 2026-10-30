"""Mongo adapter for RefreshSessionRepository.

Writes exactly the document shape the API's session store wrote before the
port existed (camelCase fields, same index names), so live refresh sessions keep
rotating with no migration. The caller supplies the collection handle: the API
chooses it from API_AUTH_REFRESH_COLLECTION, so this adapter never names one.
"""

from datetime import datetime, timezone
from typing import Any

from pymongo.errors import OperationFailure

from ....application.repositories.refresh_session_repository import (
    RefreshSession,
    RefreshSessionRepository,
)


def _as_utc(value: datetime) -> datetime:
    """Coerce a datetime read back from Mongo to tz-aware UTC.

    pymongo returns datetimes tz-naive by default; treating naive as UTC keeps
    comparisons against the tz-aware clock valid without codec options.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _as_utc_or_none(value: datetime | None) -> datetime | None:
    return None if value is None else _as_utc(value)


class MongoRefreshSessionRepository(RefreshSessionRepository):
    """Refresh sessions in a caller-supplied pymongo collection."""

    def __init__(self, *, collection: Any) -> None:
        self._collection = collection

    def ensure_indexes(self) -> None:
        """Create the collection's indexes; idempotent (safe every startup).

        Index options are not changed in place: real Mongo raises
        ``IndexOptionsConflict`` for a same-name index with different options,
        so such a change needs a manual ``dropIndex`` first.
        """
        try:
            self._collection.create_index(
                "tokenHash", unique=True, name="uq_token_hash"
            )
            self._collection.create_index("familyId", name="ix_family_id")
            self._collection.create_index("userId", name="ix_user_id")
            self._collection.create_index(
                "expiresAt", expireAfterSeconds=0, name="ttl_expires_at"
            )
        except OperationFailure as exc:
            raise RuntimeError(
                "Failed to ensure refresh-session indexes; an existing index "
                "may have conflicting options — drop it manually and restart"
            ) from exc

    def create(self, session: RefreshSession) -> None:
        self._collection.insert_one(
            {
                "tokenHash": session.token_hash,
                "userId": session.user_id,
                "participantId": session.participant_id,
                "familyId": session.family_id,
                "parentId": session.parent_id,
                "issuedAt": session.issued_at,
                "expiresAt": session.expires_at,
                "rotatedAt": session.rotated_at,
                "revoked": session.revoked,
                "revokedAt": session.revoked_at,
                "revokedReason": session.revoked_reason,
                "userAgent": session.user_agent,
                "ip": session.ip,
                "createdBy": session.created_by,
            }
        )

    def get_by_token_hash(self, token_hash: str) -> RefreshSession | None:
        doc = self._collection.find_one({"tokenHash": token_hash})
        return None if doc is None else self._to_session(doc)

    def mark_rotated(self, session_id: str, *, rotated_at: datetime) -> bool:
        raise NotImplementedError("Task 2")

    def clear_rotated(self, session_id: str, *, rotated_at: datetime) -> None:
        raise NotImplementedError("Task 2")

    def revoke_by_token_hash(
        self, token_hash: str, *, reason: str, revoked_at: datetime
    ) -> None:
        raise NotImplementedError("Task 2")

    def revoke_family(
        self, family_id: str, *, reason: str, revoked_at: datetime
    ) -> None:
        raise NotImplementedError("Task 2")

    def revoke_all_for_user(
        self, user_id: str, *, reason: str, revoked_at: datetime
    ) -> None:
        raise NotImplementedError("Task 2")

    @staticmethod
    def _to_session(doc: dict) -> RefreshSession:
        return RefreshSession(
            id=str(doc["_id"]),
            token_hash=doc["tokenHash"],
            user_id=doc["userId"],
            participant_id=doc.get("participantId"),
            family_id=doc["familyId"],
            parent_id=doc.get("parentId"),
            issued_at=_as_utc(doc["issuedAt"]),
            expires_at=_as_utc(doc["expiresAt"]),
            rotated_at=_as_utc_or_none(doc.get("rotatedAt")),
            revoked=doc["revoked"],
            revoked_at=_as_utc_or_none(doc.get("revokedAt")),
            revoked_reason=doc.get("revokedReason"),
            user_agent=doc.get("userAgent"),
            ip=doc.get("ip"),
            created_by=doc["createdBy"],
        )
