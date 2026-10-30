"""Participant ids are strings in the domain and ObjectIds on disk (FOUND-04)."""

from __future__ import annotations

from typing import Any

import mongomock
import pytest
from bson import ObjectId
from dependency_injector import providers
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openwellness_core.adapters.mongo.repositories.mongo_participant_repository import (
    MongoParticipantRepository,
)
from openwellness_core.domain.exceptions.domain_exception import (
    EntityNotFoundException,
)
from openwellness_core.domain.models.participant import Participant


@pytest.fixture
def mongo(app: FastAPI, client: TestClient) -> tuple[TestClient, Any]:
    db = mongomock.MongoClient()["testdb"]
    repo = MongoParticipantRepository(mongo_repo=db)
    app.state.container.repositories.participant.override(providers.Object(repo))
    return client, db


def _create(client: TestClient, study: str, **extra: Any) -> Any:
    body = {"participantNumber": "P-1", **extra}
    return client.post(f"/v1/studies/{study}/participants", json=body)


def test_create_stores_objectids_and_returns_strings(mongo: Any) -> None:
    client, db = mongo
    study, user, coach = (str(ObjectId()) for _ in range(3))
    r = _create(client, study, userId=user, assignedCoachId=coach)
    assert r.status_code == 201, r.text
    body = r.json()
    assert (body["studyId"], body["userId"], body["assignedCoachId"]) == (
        study,
        user,
        coach,
    )
    doc = db["participants"].find_one()
    assert doc["studyId"] == ObjectId(study)
    assert doc["userId"] == ObjectId(user)
    assert doc["assignedCoachId"] == ObjectId(coach)


def test_get_and_list_return_created(mongo: Any) -> None:
    client, _ = mongo
    study = str(ObjectId())
    created = _create(client, study).json()
    pid = created["name"].rsplit("/", 1)[-1]
    got = client.get(f"/v1/studies/{study}/participants/{pid}")
    assert got.status_code == 200
    listed = client.get(f"/v1/studies/{study}/participants").json()
    assert [p["name"] for p in listed["participants"]] == [created["name"]]


def test_get_under_other_study_is_404(mongo: Any) -> None:
    client, _ = mongo
    study = str(ObjectId())
    pid = _create(client, study).json()["name"].rsplit("/", 1)[-1]
    r = client.get(f"/v1/studies/{ObjectId()}/participants/{pid}")
    assert r.status_code == 404


def test_malformed_study_on_create_is_404(mongo: Any) -> None:
    client, _ = mongo
    assert _create(client, "not-hex").status_code == 404


def test_malformed_reference_on_create_is_404(mongo: Any) -> None:
    client, _ = mongo
    assert _create(client, str(ObjectId()), userId="bad").status_code == 404


def test_list_under_malformed_study_is_empty(mongo: Any) -> None:
    client, _ = mongo
    r = client.get("/v1/studies/not-hex/participants")
    assert r.status_code == 200
    assert r.json()["participants"] == []


def test_adapter_refuses_empty_study_id() -> None:
    db = mongomock.MongoClient()["testdb"]
    repo = MongoParticipantRepository(mongo_repo=db)
    with pytest.raises(EntityNotFoundException):
        repo.create(Participant(participant_number="N-1"))
    assert db["participants"].count_documents({}) == 0
