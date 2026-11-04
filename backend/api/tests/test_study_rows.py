"""Study-parented rows under the policy engine (AUTH-05, AUTH-06, ADR 0007).

``participant``, ``study``, ``study_message`` and ``study_settings``: study scope
comes from the signed ``coach_studies`` claim or the caller's own Participant, a
coach cannot relink a participant, and ``:lookup`` answers a study out of scope
exactly as it answers one that does not exist.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI

from .conftest import STUDY_A, STUDY_B, TEST_ADMIN_ID, World

P = "/v1/studies/{study}/participants"


def _participant_url(study: str, pid: str = "") -> str:
    return P.format(study=study) + (f"/{pid}" if pid else "")


# -- participant ---------------------------------------------------------------


def test_coach_lists_participants_in_study(app: FastAPI, world: World) -> None:
    coach = world.client(app, "coach_in")
    resp = coach.get(_participant_url(STUDY_A))
    assert resp.status_code == 200, resp.text
    assert [p["name"].rsplit("/", 1)[1] for p in resp.json()["participants"]] == [
        "p-a"
    ]
    assert coach.get(_participant_url(STUDY_B)).status_code == 404


def test_coach_patches_participant_in_study(app: FastAPI, world: World) -> None:
    url = _participant_url(STUDY_A, "p-a")
    resp = world.client(app, "coach_in").patch(url, json={"isActive": False})
    assert resp.status_code == 200, resp.text
    assert resp.json()["isActive"] is False
    assert world.client(app, "coach_other").patch(url, json={}).status_code == 404


def test_coach_patch_ignores_user_id(app: FastAPI, world: World) -> None:
    url = _participant_url(STUDY_A, "p-a")
    stored = app.state.container.repositories.participant().store["p-a"]
    resp = world.client(app, "coach_in").patch(url, json={"userId": "u-b"})
    assert resp.status_code == 200, resp.text
    assert stored.user_id == "u-a"
    resp = world.client(app, "admin").patch(url, json={"userId": "u-b"})
    assert resp.status_code == 200, resp.text
    assert stored.user_id == "u-b"


def test_participant_reads_own_record(app: FastAPI, world: World) -> None:
    url = _participant_url(STUDY_A, "p-a")
    assert world.client(app, "owner_self").get(url).status_code == 200
    assert world.client(app, "owner_other").get(url).status_code == 404


def test_participant_list_is_403_for_any_study(
    app: FastAPI, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = app.state.container.repositories.participant()

    def boom(*_: Any, **__: Any) -> Any:
        raise AssertionError("A1: a participant's list must not read")

    monkeypatch.setattr(repo, "get_by_id", boom)
    monkeypatch.setattr(repo, "get_by_study_id", boom)
    bodies = set()
    for caller in ("owner_self", "owner_other"):
        client = world.client(app, caller)
        for study in (STUDY_A, STUDY_B, "no-such-study"):
            for resp in (
                client.get(_participant_url(study)),
                client.post(_participant_url(study), json={}),
            ):
                assert resp.status_code == 403, (caller, study, resp.text)
                bodies.add(resp.text)
    assert len(bodies) == 1


def test_participant_under_wrong_study_is_404(app: FastAPI, world: World) -> None:
    resp = world.client(app, "coach_both").get(_participant_url(STUDY_B, "p-a"))
    assert resp.status_code == 404


# -- study ----------------------------------------------------------------------

L = "/v1/studies:lookup"


def test_coach_study_list_is_scoped(app: FastAPI, world: World) -> None:
    resp = world.client(app, "coach_in").get("/v1/studies")
    assert resp.status_code == 200, resp.text
    assert [s["name"] for s in resp.json()["studies"]] == [f"studies/{STUDY_A}"]
    resp = world.client(app, "coach_empty").get("/v1/studies")
    assert resp.status_code == 200, resp.text
    assert resp.json()["studies"] == []


def test_lookup_scope(app: FastAPI, world: World) -> None:
    for caller, status in (
        ("owner_self", 200),
        ("coach_in", 200),
        ("owner_other", 404),
        ("coach_other", 404),
    ):
        resp = world.client(app, caller).post(L, json={"name": STUDY_A})
        assert resp.status_code == status, (caller, resp.text)


def test_lookup_denied_matches_missing(app: FastAPI, world: World) -> None:
    coach = world.client(app, "coach_other")
    denied = coach.post(L, json={"name": STUDY_A})
    missing = coach.post(L, json={"name": "no-such-study"})
    assert denied.status_code == missing.status_code == 404
    assert denied.text.replace(STUDY_A, "X") == missing.text.replace(
        "no-such-study", "X"
    )


def test_lookup_regex_is_escaped() -> None:
    from datetime import datetime

    import mongomock

    from openwellness_core.adapters.mongo.repositories.mongo_study_repository import (
        MongoStudyRepository,
    )
    from openwellness_core.domain.models.study import Study

    repo = MongoStudyRepository(mongo_repo=mongomock.MongoClient()["testdb"])
    for name in ("Alpha", "Beta"):
        repo.create(Study(app_id="app", name=name, time_created=datetime.now()))
    assert repo.get_by_name(".*") is None
    found = repo.get_by_name("alpha")
    assert found is not None and found.name == "Alpha"


def test_study_updated_by_from_token(app: FastAPI, world: World) -> None:
    admin = world.client(app, "admin")
    body = {
        "appId": "app",
        "name": "S",
        "timeCreated": "2026-01-01T00:00:00Z",
        "updatedBy": "forged",
    }
    resp = admin.post("/v1/studies", json=body)
    assert resp.status_code == 201, resp.text
    assert resp.json()["updatedBy"] == TEST_ADMIN_ID
    resp = admin.patch(
        f"/v1/studies/{STUDY_A}", json={"description": "d", "updatedBy": "forged"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["updatedBy"] == TEST_ADMIN_ID


# -- study_settings and study_message ---------------------------------------------

SETTINGS = "/v1/studies/{study}/studySettings"
MESSAGES = "/v1/studies/{study}/studyMessages"


def test_study_settings_binding(app: FastAPI, world: World) -> None:
    coach = world.client(app, "coach_in")
    resp = coach.post(SETTINGS.format(study=STUDY_A), json={})
    assert resp.status_code == 201, resp.text
    assert (resp.json()["owner"], resp.json()["studyId"]) == (STUDY_A, STUDY_A)
    # The body's studyId is not a wire field: it is dropped, never trusted.
    resp = coach.post(SETTINGS.format(study=STUDY_A), json={"studyId": STUDY_B})
    assert resp.status_code == 201, resp.text
    assert resp.json()["studyId"] == STUDY_A
    other = world.client(app, "coach_other")
    assert other.post(SETTINGS.format(study=STUDY_A), json={}).status_code == 404


def test_study_message_scope(app: FastAPI, world: World) -> None:
    owner = world.client(app, "owner_self")
    assert owner.get(MESSAGES.format(study=STUDY_A)).status_code == 200
    assert owner.get(MESSAGES.format(study=STUDY_B)).status_code == 404
    resp = world.client(app, "coach_in").post(
        MESSAGES.format(study=STUDY_A),
        json={"message": "hi", "messageType": 0, "timeCreated": "2026-01-01T00:00:00Z"},
    )
    assert resp.status_code == 201, resp.text


def test_self_study_fail_closed(app: FastAPI, world: World) -> None:
    owner = world.client(app, "owner_self")
    url = SETTINGS.format(study=STUDY_A)
    assert owner.get(url).status_code == 200
    participants = app.state.container.repositories.participant()
    participants.store["p-a"].study_id = ""
    assert owner.get(url).status_code == 404
    del participants.store["p-a"]
    assert owner.get(url).status_code == 404
