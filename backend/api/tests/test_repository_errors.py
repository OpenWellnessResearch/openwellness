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


def test_outage_on_list_returns_500_not_empty_list(down_client: TestClient) -> None:
    r = down_client.get("/v1/users")
    assert r.status_code == 500
    assert r.json()["error"]["status"] == "INTERNAL"
