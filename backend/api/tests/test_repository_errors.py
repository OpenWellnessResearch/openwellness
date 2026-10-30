"""Repository errors are honest (FOUND-06).

A malformed id means "no such document" (404). A datastore outage must surface
as a logged 5xx, never as a 404 or an empty list.
"""

from __future__ import annotations

import logging
from typing import Any

import mongomock
import pytest
from bson import ObjectId
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pymongo.errors import ServerSelectionTimeoutError

from openwellness_core.adapters.mongo.repositories.mongo_user_repository import (
    MongoUserRepository,
)
from openwellness_core.domain.models.user import User

_DRIVER_DETAIL = "mongo-host-detail down"


class _DownCollection:
    """Every datastore call raises, like a Mongo node that is unreachable."""

    def _boom(self, *args: Any, **kwargs: Any) -> Any:
        raise ServerSelectionTimeoutError(_DRIVER_DETAIL)

    find_one = find = insert_one = update_one = delete_one = delete_many = _boom


class _DownDb:
    def __getitem__(self, name: str) -> _DownCollection:
        return _DownCollection()


def _use_repo(app: FastAPI, db: Any) -> MongoUserRepository:
    repo = MongoUserRepository(repo=db)
    app.state.container.repositories.user.override(providers.Object(repo))
    return repo


@pytest.fixture
def mongo_repo(app: FastAPI) -> MongoUserRepository:
    return _use_repo(app, mongomock.MongoClient()["testdb"])


@pytest.fixture
def down_client(app: FastAPI) -> TestClient:
    _use_repo(app, _DownDb())
    return TestClient(app, raise_server_exceptions=False)


def test_malformed_id_returns_404(client: TestClient, mongo_repo: Any) -> None:
    r = client.get("/v1/users/not-an-object-id")
    assert r.status_code == 404
    assert r.json()["error"]["status"] == "NOT_FOUND"


def test_unknown_valid_id_returns_404(client: TestClient, mongo_repo: Any) -> None:
    r = client.get(f"/v1/users/{ObjectId()}")
    assert r.status_code == 404


def test_existing_user_is_returned(client: TestClient, mongo_repo: Any) -> None:
    created = mongo_repo.create(
        User(email="a@example.com", is_active=True, username="a")
    )
    r = client.get(f"/v1/users/{created.id}")
    assert r.status_code == 200


def test_outage_on_get_returns_logged_500(
    down_client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        r = down_client.get(f"/v1/users/{ObjectId()}")
    assert r.status_code == 500
    assert r.json()["error"]["status"] == "INTERNAL"
    assert "mongo-host-detail" not in r.text
    assert any(
        rec.name == "openwellness_api.errors.handlers"
        and "ServerSelectionTimeoutError" in rec.getMessage()
        for rec in caplog.records
    )


def test_500_carries_cors_headers_for_allowed_origin_only(
    down_client: TestClient,
) -> None:
    url = f"/v1/users/{ObjectId()}"
    ok = down_client.get(url, headers={"Origin": "http://localhost:5173"})
    assert ok.status_code == 500
    assert ok.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = down_client.get(url, headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_outage_on_list_returns_500_not_empty_list(down_client: TestClient) -> None:
    r = down_client.get("/v1/users")
    assert r.status_code == 500
    assert r.json()["error"]["status"] == "INTERNAL"


# --- Task 2: every id conversion is guarded --------------------------------- #

from openwellness_core.adapters.mongo.repositories.mongo_device_repository import (
    MongoDeviceRepository,
)
from openwellness_core.adapters.mongo.repositories.mongo_participant_repository import (
    MongoParticipantRepository,
)
from openwellness_core.domain.exceptions.domain_exception import (
    EntityNotFoundException,
)


def _db() -> Any:
    return mongomock.MongoClient()["testdb"]


def test_save_with_malformed_id_raises_not_found() -> None:
    repo = MongoUserRepository(repo=_db())
    with pytest.raises(EntityNotFoundException):
        repo.save(User(id="bad", email="x@example.com", is_active=True, username="x"))


def test_delete_with_malformed_id_raises_not_found() -> None:
    with pytest.raises(EntityNotFoundException):
        MongoUserRepository(repo=_db()).delete("bad")


def test_unarchive_with_malformed_id_is_noop_without_db_access() -> None:
    assert MongoUserRepository(repo=_DownDb()).unarchive("bad") is None


def test_device_by_malformed_participant_id_returns_empty() -> None:
    repo = MongoDeviceRepository(mongo_repo=_db())
    assert repo.get_by_participant_id("bad") == []


def test_participant_lookups_with_malformed_study_id_return_nothing() -> None:
    repo = MongoParticipantRepository(mongo_repo=_db())
    assert repo.get_by_study_id("bad") == []
    assert repo.get_by_num_study_id("A-1", "bad") is None


def test_outage_on_delete_and_unarchive_propagates() -> None:
    repo = MongoUserRepository(repo=_DownDb())
    with pytest.raises(ServerSelectionTimeoutError):
        repo.delete(str(ObjectId()))
    with pytest.raises(ServerSelectionTimeoutError):
        repo.unarchive(str(ObjectId()))


def test_delete_malformed_id_through_api_returns_404(
    client: TestClient, mongo_repo: Any
) -> None:
    r = client.delete("/v1/users/not-an-object-id")
    assert r.status_code == 404


# --- Duplicate-key collisions become DuplicateEntityException ---------------- #

from pymongo.errors import DuplicateKeyError

from openwellness_core.application.exceptions import DuplicateEntityException

_DUP_EMAIL = "a@example.com"


def _unique_email_repo() -> MongoUserRepository:
    db = _db()
    db["users"].create_index("email", unique=True)
    return MongoUserRepository(repo=db)


def test_create_duplicate_email_raises_duplicate_entity() -> None:
    repo = _unique_email_repo()
    repo.create(User(email=_DUP_EMAIL, is_active=True, username="a"))
    with pytest.raises(DuplicateEntityException) as ei:
        repo.create(User(email=_DUP_EMAIL, is_active=True, username="b"))
    assert isinstance(ei.value.__cause__, DuplicateKeyError)
    assert _DUP_EMAIL not in str(ei.value)


def test_save_to_existing_email_raises_duplicate_entity() -> None:
    repo = _unique_email_repo()
    repo.create(User(email=_DUP_EMAIL, is_active=True, username="a"))
    other = repo.create(User(email="b@example.com", is_active=True, username="b"))
    other.email = _DUP_EMAIL
    with pytest.raises(DuplicateEntityException) as ei:
        repo.save(other)
    assert _DUP_EMAIL not in str(ei.value)


def test_duplicate_email_post_returns_409_without_the_email(
    client: TestClient, app: FastAPI
) -> None:
    db = _db()
    db["users"].create_index("email", unique=True)
    _use_repo(app, db)
    body = {"email": _DUP_EMAIL, "isActive": True, "username": "a"}
    assert client.post("/v1/users", json=body).status_code == 201
    r = client.post("/v1/users", json=body)
    assert r.status_code == 409, r.text
    assert r.json()["error"]["status"] == "ALREADY_EXISTS"
    assert _DUP_EMAIL not in r.text
