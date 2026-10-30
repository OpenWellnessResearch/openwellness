"""Contract tests for MongoRefreshSessionRepository over mongomock.

These pin the persisted document shape and index names that live refresh
sessions depend on, plus the single-use rotation and revocation contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import mongomock
import pytest

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


def test_mark_rotated_is_single_use() -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.create(_session())
    sid = repo.get_by_token_hash("h1").id  # type: ignore[union-attr]

    assert repo.mark_rotated(sid, rotated_at=NOW) is True
    assert repo.mark_rotated(sid, rotated_at=LATER) is False
    assert _stored(coll, "h1")["rotatedAt"] == NOW.replace(tzinfo=None)


def test_mark_rotated_false_on_revoked_session_and_writes_nothing() -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.create(_session())
    repo.revoke_by_token_hash("h1", reason="logout", revoked_at=NOW)
    sid = repo.get_by_token_hash("h1").id  # type: ignore[union-attr]

    assert repo.mark_rotated(sid, rotated_at=NOW) is False
    assert _stored(coll, "h1")["rotatedAt"] is None


def test_mark_rotated_false_on_malformed_id() -> None:
    assert _repo().mark_rotated("not-an-object-id", rotated_at=NOW) is False


def test_clear_rotated_only_while_value_matches() -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.create(_session())
    sid = repo.get_by_token_hash("h1").id  # type: ignore[union-attr]
    repo.mark_rotated(sid, rotated_at=NOW)

    repo.clear_rotated(sid, rotated_at=LATER)  # stale value: no-op
    assert _stored(coll, "h1")["rotatedAt"] is not None

    repo.clear_rotated(sid, rotated_at=NOW)
    assert _stored(coll, "h1")["rotatedAt"] is None

    repo.clear_rotated("not-an-object-id", rotated_at=NOW)  # no-op, no raise


def test_revoke_by_token_hash_touches_that_session_only() -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.create(_session("h1"))
    repo.create(_session("h2"))

    repo.revoke_by_token_hash("h1", reason="logout", revoked_at=NOW)

    h1, h2 = _stored(coll, "h1"), _stored(coll, "h2")
    assert h1["revoked"] is True
    assert h1["revokedAt"] == NOW.replace(tzinfo=None)
    assert h1["revokedReason"] == "logout"
    assert h2["revoked"] is False


@pytest.mark.parametrize("scope", ["family", "user"])
def test_bulk_revoke_is_scoped(scope: str) -> None:
    coll = _collection()
    repo = _repo(coll)
    repo.create(_session("in1"))
    repo.create(_session("in2"))
    repo.create(_session("out", family_id="f2", user_id="u2"))

    if scope == "family":
        repo.revoke_family("f1", reason="reuse_detected", revoked_at=NOW)
    else:
        repo.revoke_all_for_user("u1", reason="logout_all", revoked_at=NOW)

    assert _stored(coll, "in1")["revoked"] is True
    assert _stored(coll, "in2")["revoked"] is True
    assert _stored(coll, "out")["revoked"] is False
