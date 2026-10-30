"""Contract tests for MongoRefreshSessionRepository over mongomock.

These pin the persisted document shape and index names that live refresh
sessions depend on, plus the single-use rotation and revocation contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import mongomock

from openwellness_core.adapters.mongo.repositories import (
    MongoRefreshSessionRepository,
)
from openwellness_core.application.repositories import (
    RefreshSession,
    RefreshSessionRepository,
)

NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 6, 1, 13, 0, 0, tzinfo=timezone.utc)
# Far-future: mongomock sweeps TTL docs by wall-clock time.
FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)

DOC_KEYS = {
    "_id", "tokenHash", "userId", "participantId", "familyId", "parentId",
    "issuedAt", "expiresAt", "rotatedAt", "revoked", "revokedAt",
    "revokedReason", "userAgent", "ip", "createdBy",
}  # fmt: skip


def _collection() -> Any:
    return mongomock.MongoClient()["testdb"]["auth_refresh_sessions"]


def _session(token_hash: str = "h1", **overrides: Any) -> RefreshSession:
    fields: dict[str, Any] = dict(
        token_hash=token_hash,
        user_id="u1",
        participant_id="p1",
        family_id="f1",
        parent_id=None,
        issued_at=NOW,
        expires_at=FUTURE,
        user_agent="ua",
        ip="127.0.0.1",
        created_by="u1",
    )
    fields.update(overrides)
    return RefreshSession(**fields)


def _repo(collection: Any | None = None) -> MongoRefreshSessionRepository:
    return MongoRefreshSessionRepository(
        collection=collection if collection is not None else _collection()
    )


def _stored(coll: Any, token_hash: str) -> dict:
    return coll.find_one({"tokenHash": token_hash})


def test_is_a_refresh_session_repository() -> None:
    assert isinstance(_repo(), RefreshSessionRepository)


def test_create_then_get_round_trips_with_aware_datetimes() -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.create(_session())

    got = repo.get_by_token_hash("h1")

    assert got is not None
    assert got.id == str(_stored(coll, "h1")["_id"])
    assert got == _session(id=got.id)
    assert got.issued_at.tzinfo is not None
    assert got.expires_at.tzinfo is not None
    assert set(_stored(coll, "h1")) == DOC_KEYS


def test_get_by_token_hash_unknown_returns_none() -> None:
    assert _repo().get_by_token_hash("nope") is None


def test_ensure_indexes_creates_named_indexes_and_is_idempotent() -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.ensure_indexes()
    repo.ensure_indexes()

    info = coll.index_information()
    assert info["uq_token_hash"].get("unique") is True
    assert "ix_family_id" in info
    assert "ix_user_id" in info
    assert "ttl_expires_at" in info
    assert info["ttl_expires_at"].get("expireAfterSeconds") == 0
