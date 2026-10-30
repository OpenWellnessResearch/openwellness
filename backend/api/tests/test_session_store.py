"""Unit tests for ``RefreshSessionStore`` (Mongo rotation + reuse detection).

Strict-TDD coverage exercising the real ``mongomock`` backend (a faithful
in-memory pymongo) so the rotation compare-and-set, single-use guarantee,
reuse → whole-family revoke, the belt-and-suspenders ``expiresAt`` check, and
the revocation helpers are genuinely run against pymongo semantics rather than
hand-mocked ``find_one``/``update_one`` stubs.

The CAS-race case (the doc looks rotatable at read time but the conditional
update matches zero) is impossible to provoke from a single thread against
mongomock, so it is simulated with a thin wrapper collection that mutates the
doc out-of-band between the ``find_one`` and the CAS ``update_one`` — that is
the *only* place a collection method is wrapped; every other test uses the raw
mongomock collection.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import mongomock
import pymongo.errors
import pytest

from openwellness_core.adapters.mongo.repositories.mongo_refresh_session_repository import (
    MongoRefreshSessionRepository,
)

from openwellness_api.auth.session_store import (
    RefreshInvalid,
    RefreshReuse,
    RefreshSessionStore,
    RotationResult,
)


FIXED_NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
# Fixed far-future: mongomock sweeps TTL-indexed docs by real wall-clock time,
# so a FIXED_NOW-relative expiry becomes a time bomb once that date passes.
FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)

# pymongo (and mongomock, faithfully) store datetimes as UTC and return them
# tz-*naive* on read with default codec options. The store writes the tz-aware
# clock value; on round-trip it comes back stripped of tzinfo. Assertions on
# *stored* timestamps therefore compare against the naive-UTC form.
STORED_NOW = FIXED_NOW.replace(tzinfo=None)
STORED_FUTURE = FUTURE.replace(tzinfo=None)


def _collection() -> Any:
    return mongomock.MongoClient()["testdb"]["auth_refresh_sessions"]


def _store(
    *,
    collection: Any | None = None,
    clock: Callable[[], datetime] | None = None,
) -> RefreshSessionStore:
    return RefreshSessionStore(
        repo=MongoRefreshSessionRepository(
            collection=collection if collection is not None else _collection()
        ),
        clock=clock or (lambda: FIXED_NOW),
    )


def _ensure_indexes(collection: Any) -> None:
    MongoRefreshSessionRepository(collection=collection).ensure_indexes()


def _create_initial(
    store: RefreshSessionStore,
    *,
    token_hash: str = "hashA",
    user_id: str = "user-1",
    participant_id: str | None = "participant-1",
    family_id: str = "fam-F",
    expires_at: datetime = FUTURE,
    user_agent: str | None = "agent/1.0",
    ip: str | None = "10.0.0.1",
) -> None:
    store.create(
        token_hash=token_hash,
        user_id=user_id,
        participant_id=participant_id,
        family_id=family_id,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
        created_by=user_id,
    )


# --------------------------------------------------------------------------- #
# ensure_indexes
# --------------------------------------------------------------------------- #
def test_ensure_indexes_declares_expected_indexes() -> None:
    collection = _collection()
    _ensure_indexes(collection)

    info = collection.index_information()

    # tokenHash: unique.
    token_idx = next(
        v for v in info.values() if v["key"] == [("tokenHash", 1)]
    )
    assert token_idx.get("unique") is True

    # familyId and userId: plain indexes present.
    assert any(v["key"] == [("familyId", 1)] for v in info.values())
    assert any(v["key"] == [("userId", 1)] for v in info.values())

    # expiresAt: TTL index with expireAfterSeconds == 0.
    ttl_idx = next(
        v for v in info.values() if v["key"] == [("expiresAt", 1)]
    )
    assert ttl_idx.get("expireAfterSeconds") == 0


def test_ensure_indexes_is_idempotent() -> None:
    collection = _collection()
    _ensure_indexes(collection)
    _ensure_indexes(collection)  # must not raise


# --------------------------------------------------------------------------- #
# create + happy rotation
# --------------------------------------------------------------------------- #
def test_create_writes_fresh_session_document() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store)

    doc = collection.find_one({"tokenHash": "hashA"})
    assert doc is not None
    assert doc["userId"] == "user-1"
    assert doc["participantId"] == "participant-1"
    assert doc["familyId"] == "fam-F"
    assert doc["parentId"] is None
    assert doc["issuedAt"] == STORED_NOW
    assert doc["expiresAt"] == STORED_FUTURE
    assert doc["rotatedAt"] is None
    assert doc["revoked"] is False
    assert doc["revokedAt"] is None
    assert doc["revokedReason"] is None
    assert doc["userAgent"] == "agent/1.0"
    assert doc["ip"] == "10.0.0.1"
    assert doc["createdBy"] == "user-1"


def test_happy_rotation_rotates_old_and_inserts_child() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store)

    old = collection.find_one({"tokenHash": "hashA"})
    assert old is not None

    result = store.consume_for_rotation(
        presented_hash="hashA",
        new_token_hash="hashB",
        new_expires_at=FUTURE,
        user_agent="agent/2.0",
        ip="10.0.0.2",
    )

    assert isinstance(result, RotationResult)
    assert result.user_id == "user-1"
    assert result.participant_id == "participant-1"
    assert result.family_id == "fam-F"

    # Old session A is now rotated (consumed) but not revoked.
    old_after = collection.find_one({"tokenHash": "hashA"})
    assert old_after is not None
    assert old_after["rotatedAt"] == STORED_NOW
    assert old_after["revoked"] is False

    # New session B: same family, parent points at old _id, fresh and live.
    new = collection.find_one({"tokenHash": "hashB"})
    assert new is not None
    assert new["familyId"] == "fam-F"
    assert new["parentId"] == str(old["_id"])
    assert new["rotatedAt"] is None
    assert new["revoked"] is False
    assert new["userId"] == "user-1"
    assert new["participantId"] == "participant-1"
    assert new["expiresAt"] == STORED_FUTURE
    assert new["userAgent"] == "agent/2.0"
    assert new["ip"] == "10.0.0.2"


# --------------------------------------------------------------------------- #
# single rotation per token (reuse → family revoke)
# --------------------------------------------------------------------------- #
def test_reusing_rotated_token_revokes_whole_family() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store)

    store.consume_for_rotation(
        presented_hash="hashA", new_token_hash="hashB", new_expires_at=FUTURE
    )

    # Presenting A again (now rotated) is reuse → RefreshReuse.
    with pytest.raises(RefreshReuse):
        store.consume_for_rotation(
            presented_hash="hashA",
            new_token_hash="hashC",
            new_expires_at=FUTURE,
        )

    # Both A and B (the entire family F) are now revoked for reuse.
    for token in ("hashA", "hashB"):
        doc = collection.find_one({"tokenHash": token})
        assert doc is not None
        assert doc["revoked"] is True
        assert doc["revokedReason"] == "reuse_detected"
        assert doc["revokedAt"] == STORED_NOW

    # No child hashC was minted from a reuse attempt.
    assert collection.find_one({"tokenHash": "hashC"}) is None


# --------------------------------------------------------------------------- #
# rotating a revoked token → reuse
# --------------------------------------------------------------------------- #
def test_rotating_revoked_token_is_reuse() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store)
    # Add a sibling in the same family to prove the whole family is revoked.
    _create_initial(
        store, token_hash="hashSib", family_id="fam-F", expires_at=FUTURE
    )

    store.revoke_by_hash("hashA", reason="logout")

    with pytest.raises(RefreshReuse):
        store.consume_for_rotation(
            presented_hash="hashA",
            new_token_hash="hashB",
            new_expires_at=FUTURE,
        )

    for token in ("hashA", "hashSib"):
        doc = collection.find_one({"tokenHash": token})
        assert doc is not None
        assert doc["revoked"] is True
        assert doc["revokedReason"] == "reuse_detected"


# --------------------------------------------------------------------------- #
# not found
# --------------------------------------------------------------------------- #
def test_consume_unknown_hash_raises_invalid() -> None:
    store = _store()
    with pytest.raises(RefreshInvalid):
        store.consume_for_rotation(
            presented_hash="nope",
            new_token_hash="hashB",
            new_expires_at=FUTURE,
        )


# --------------------------------------------------------------------------- #
# expired (belt-and-suspenders beyond the TTL index)
# --------------------------------------------------------------------------- #
def test_consume_expired_token_raises_invalid_not_reuse() -> None:
    collection = _collection()
    store = _store(collection=collection)
    # Live session, but already past its expiry — TTL index never sweeps in
    # mongomock, so only the explicit expiresAt check protects us here.
    past_expiry = FIXED_NOW - timedelta(seconds=1)
    _create_initial(store, expires_at=past_expiry)

    with pytest.raises(RefreshInvalid):
        store.consume_for_rotation(
            presented_hash="hashA",
            new_token_hash="hashB",
            new_expires_at=FUTURE,
        )

    # Expiry is NOT reuse: the session was never rotated and stays un-revoked
    # (nothing to defend against — no token was ever issued from it).
    doc = collection.find_one({"tokenHash": "hashA"})
    assert doc is not None
    assert doc["rotatedAt"] is None
    assert doc["revoked"] is False


# --------------------------------------------------------------------------- #
# CAS race → reuse
# --------------------------------------------------------------------------- #
class _RaceCollection:
    """Wraps a mongomock collection to inject a lost-CAS race exactly once.

    The doc reads as rotatable (``find_one`` is untouched), but immediately
    before the store's conditional CAS ``update_one`` fires we set ``rotatedAt``
    out-of-band on the real collection. The store's filter (which requires
    ``rotatedAt: None``) then matches zero rows — modelling a concurrent
    rotation that won the race. Every other call delegates to the real
    collection so the surrounding logic and the family-revoke side effect run
    for real.
    """

    def __init__(self, inner: Any, *, now: datetime) -> None:
        self._inner = inner
        self._now = now
        self._raced = False

    def update_one(self, filter: Any, update: Any, *args: Any, **kw: Any) -> Any:
        # Only sabotage the CAS consume (the one filtered on rotatedAt: None),
        # and only the first time, so the subsequent family-revoke update_many
        # / update_one calls behave normally.
        if (
            not self._raced
            and filter.get("rotatedAt", "MISSING") is None
            and filter.get("revoked") is False
        ):
            self._raced = True
            self._inner.update_one(
                {"_id": filter["_id"]}, {"$set": {"rotatedAt": self._now}}
            )
        return self._inner.update_one(filter, update, *args, **kw)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_cas_race_is_treated_as_reuse() -> None:
    inner = _collection()
    race = _RaceCollection(inner, now=FIXED_NOW)
    store = _store(collection=race)
    _create_initial(store)

    with pytest.raises(RefreshReuse):
        store.consume_for_rotation(
            presented_hash="hashA",
            new_token_hash="hashB",
            new_expires_at=FUTURE,
        )

    # Lost CAS ⇒ the whole family is revoked for reuse.
    doc = inner.find_one({"tokenHash": "hashA"})
    assert doc is not None
    assert doc["revoked"] is True
    assert doc["revokedReason"] == "reuse_detected"


def test_cas_matched_zero_branch_revokes_family() -> None:
    """Direct unit of the matched_count==0 CAS branch via a tiny fake.

    Independent of the race-wrapper: an injected collection whose CAS
    ``update_one`` returns ``matched_count == 0`` must drive reuse + a family
    revoke, regardless of how the zero-match arose.
    """

    class _ZeroCasCollection:
        def __init__(self) -> None:
            self.revoked_family: str | None = None
            self.created = False

        def find_one(self, filter: Any) -> Any:
            return {
                "_id": "oid-1",
                "tokenHash": filter["tokenHash"],
                "userId": "user-1",
                "participantId": "participant-1",
                "familyId": "fam-F",
                "rotatedAt": None,
                "revoked": False,
                "issuedAt": FIXED_NOW,
                "expiresAt": FUTURE,
                "createdBy": "user-1",
            }

        def update_one(self, filter: Any, update: Any) -> Any:
            # The CAS filter requires rotatedAt: None → simulate a lost race.
            return type("R", (), {"matched_count": 0})()

        def update_many(self, filter: Any, update: Any) -> Any:
            self.revoked_family = filter.get("familyId")
            return type("R", (), {"matched_count": 1})()

        def insert_one(self, doc: Any) -> Any:  # pragma: no cover - guard
            self.created = True
            return type("R", (), {"inserted_id": "child"})()

    fake = _ZeroCasCollection()
    store = _store(collection=fake)

    with pytest.raises(RefreshReuse):
        store.consume_for_rotation(
            presented_hash="hashA",
            new_token_hash="hashB",
            new_expires_at=FUTURE,
        )

    assert fake.revoked_family == "fam-F"
    assert fake.created is False  # no child minted on a lost CAS


# --------------------------------------------------------------------------- #
# child insert fails after CAS → parent rolled back (no family lockout)
# --------------------------------------------------------------------------- #
class _ChildInsertFailsOnceCollection:
    """Wraps a mongomock collection so the child insert fails exactly once.

    The CAS ``update_one`` succeeds for real (parent marked rotated), then the
    *second* ``insert_one`` — the rotated child — raises once. Models a write
    error / duplicate-hash / network blip on the non-atomic child insert that
    follows a winning CAS on standalone Mongo (no transaction to wrap them).
    """

    def __init__(self, inner: Any) -> None:
        self._inner = inner
        self._inserts = 0

    def insert_one(self, doc: Any, *args: Any, **kw: Any) -> Any:
        self._inserts += 1
        # First insert (the initial session) is real; the second (the rotated
        # child) blows up once to exercise the rollback path.
        if self._inserts == 2:
            raise RuntimeError("simulated child insert failure")
        return self._inner.insert_one(doc, *args, **kw)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def test_child_insert_failure_rolls_back_parent() -> None:
    inner = _collection()
    failing = _ChildInsertFailsOnceCollection(inner)
    store = _store(collection=failing)
    _create_initial(store)  # first insert_one (real)

    # CAS succeeds, then the child insert raises → the injected error surfaces.
    with pytest.raises(RuntimeError, match="simulated child insert failure"):
        store.consume_for_rotation(
            presented_hash="hashA",
            new_token_hash="hashB",
            new_expires_at=FUTURE,
        )

    # Parent is rolled back: rotatedAt is None again and it is NOT revoked, so
    # the token is usable once more (no lockout, no reuse occurred).
    parent = inner.find_one({"tokenHash": "hashA"})
    assert parent is not None
    assert parent["rotatedAt"] is None
    assert parent["revoked"] is False

    # No orphan child was minted by the failed attempt.
    assert inner.find_one({"tokenHash": "hashB"}) is None

    # A fresh rotation with the SAME presented token now succeeds and mints the
    # child (the failure window has passed; only the 2nd insert was sabotaged).
    result = store.consume_for_rotation(
        presented_hash="hashA",
        new_token_hash="hashB",
        new_expires_at=FUTURE,
    )
    assert isinstance(result, RotationResult)
    assert result.family_id == "fam-F"

    child = inner.find_one({"tokenHash": "hashB"})
    assert child is not None
    assert child["familyId"] == "fam-F"
    assert child["revoked"] is False
    assert child["rotatedAt"] is None

    # The parent is now legitimately consumed (rotated) and still not revoked.
    parent_after = inner.find_one({"tokenHash": "hashA"})
    assert parent_after is not None
    assert parent_after["rotatedAt"] == STORED_NOW
    assert parent_after["revoked"] is False


# --------------------------------------------------------------------------- #
# revoke_by_hash
# --------------------------------------------------------------------------- #
def test_revoke_by_hash_is_idempotent() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store)

    store.revoke_by_hash("hashA")
    doc = collection.find_one({"tokenHash": "hashA"})
    assert doc is not None
    assert doc["revoked"] is True
    assert doc["revokedReason"] == "logout"
    assert doc["revokedAt"] == STORED_NOW

    # Revoking again is fine, and revoking a missing token does not raise.
    store.revoke_by_hash("hashA")
    store.revoke_by_hash("does-not-exist")


def test_revoke_by_hash_custom_reason() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store)

    store.revoke_by_hash("hashA", reason="admin")
    doc = collection.find_one({"tokenHash": "hashA"})
    assert doc is not None
    assert doc["revokedReason"] == "admin"


# --------------------------------------------------------------------------- #
# revoke_family
# --------------------------------------------------------------------------- #
def test_revoke_family_revokes_all_in_family_only() -> None:
    collection = _collection()
    store = _store(collection=collection)
    _create_initial(store, token_hash="a1", family_id="fam-F")
    _create_initial(store, token_hash="a2", family_id="fam-F")
    _create_initial(store, token_hash="b1", family_id="fam-G")

    store.revoke_family("fam-F", reason="reuse_detected")

    for token in ("a1", "a2"):
        doc = collection.find_one({"tokenHash": token})
        assert doc is not None
        assert doc["revoked"] is True
        assert doc["revokedReason"] == "reuse_detected"

    other = collection.find_one({"tokenHash": "b1"})
    assert other is not None
    assert other["revoked"] is False


# --------------------------------------------------------------------------- #
# revoke_all_for_user
# --------------------------------------------------------------------------- #
def test_revoke_all_for_user_scopes_to_user() -> None:
    collection = _collection()
    store = _store(collection=collection)
    # Two families for user-1, one family for user-2.
    _create_initial(store, token_hash="u1f1", user_id="user-1", family_id="f1")
    _create_initial(store, token_hash="u1f2", user_id="user-1", family_id="f2")
    _create_initial(store, token_hash="u2f3", user_id="user-2", family_id="f3")

    store.revoke_all_for_user("user-1")

    for token in ("u1f1", "u1f2"):
        doc = collection.find_one({"tokenHash": token})
        assert doc is not None
        assert doc["revoked"] is True
        assert doc["revokedReason"] == "logout_all"

    other = collection.find_one({"tokenHash": "u2f3"})
    assert other is not None
    assert other["revoked"] is False


# --------------------------------------------------------------------------- #
# unique tokenHash — mongomock 4.3.0 DOES enforce unique indexes
# --------------------------------------------------------------------------- #
def test_unique_token_hash_is_enforced() -> None:
    # Confirmed: mongomock 4.3.0 enforces the unique index and raises
    # pymongo.errors.DuplicateKeyError, mirroring real Mongo. (Were a future
    # mongomock to drop enforcement, this would need a skip — the unique index
    # is still declared in ensure_indexes() and enforced by real Mongo.)
    collection = _collection()
    store = _store(collection=collection)
    _ensure_indexes(collection)
    _create_initial(store, token_hash="dup")

    with pytest.raises(pymongo.errors.DuplicateKeyError):
        _create_initial(store, token_hash="dup", family_id="fam-OTHER")
