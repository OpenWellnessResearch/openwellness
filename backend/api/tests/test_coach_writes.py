"""Coach write check over HTTP (AUTH-05, ADR 0007 ``coach-study`` write rules).

A coach writes coach-authored rows only for a participant whose own
``Participant.study_id`` is in ``coach_studies``; the body's ``studyId`` is never
trusted. Participants read these rows and cannot write them (D-06).
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .conftest import STUDY_A, STUDY_B, World

C = "/v1/users/p-a/conditions"
M = "/v1/users/p-a/messages"


def _id(resp: Any) -> str:
    assert resp.status_code == 201, resp.text
    return resp.json()["name"].rsplit("/", 1)[1]


def test_coach_creates_condition_in_study(app: FastAPI, world: World) -> None:
    resp = world.client(app, "coach_in").post(C, json={"week": 1})
    assert resp.status_code == 201, resp.text
    assert resp.json()["studyId"] == STUDY_A
    assert resp.json()["updatedBy"] == "u-ci"


def test_coach_create_other_study_participant_is_404(
    app: FastAPI, world: World
) -> None:
    client = world.client(app, "coach_in")
    assert client.post("/v1/users/p-b/conditions", json={"week": 1}).status_code == 404
    resp = client.post(
        "/v1/users/p-b/conditions", json={"week": 1, "studyId": STUDY_A}
    )
    assert resp.status_code == 404


def test_coach_supplied_study_cannot_cross(app: FastAPI, world: World) -> None:
    # coach_both holds both studies, but p-a is enrolled in A: a body naming B is 404.
    resp = world.client(app, "coach_both").post(C, json={"studyId": STUDY_B})
    assert resp.status_code == 404


def test_coach_patch_after_owner_moved_is_404(app: FastAPI, world: World) -> None:
    id_ = _id(world.client(app, "coach_in").post(C, json={"week": 1}))
    # The owner leaves study A: the record keeps study A, the Participant does not.
    app.state.container.repositories.participant().store["p-a"].study_id = STUDY_B
    coach = world.client(app, "coach_in")
    assert coach.patch(f"{C}/{id_}", json={"week": 2}).status_code == 404
    assert coach.delete(f"{C}/{id_}").status_code == 404
    assert coach.get(f"{C}/{id_}").status_code == 200


def test_participant_reads_own_condition_only(app: FastAPI, world: World) -> None:
    owner = world.client(app, "owner_self")
    assert owner.get(C).status_code == 200
    assert owner.post(C, json={"week": 1}).status_code == 403
    assert owner.post("/v1/users/p-b/conditions", json={}).status_code == 404
    assert owner.get("/v1/users/p-b/conditions").status_code == 404


def test_participant_cannot_file_under_other_study(app: FastAPI, world: World) -> None:
    resp = world.client(app, "owner_self").post(
        "/v1/users/p-a/weights",
        json={"weight": 70.0, "studyId": STUDY_B},
    )
    assert resp.status_code == 404


def _message(app: FastAPI, world: World, subtype: int, study: str) -> str:
    """Create a message under p-a as admin, then pin its study (the owner's is A)."""
    id_ = _id(
        world.client(app, "admin").post(M, json={"body": "hi", "subtype": subtype})
    )
    app.state.container.repositories.message().store[id_].study_id = study
    return id_


def _ids(resp: Any) -> set[str]:
    assert resp.status_code == 200, resp.text
    return {m["name"].rsplit("/", 1)[1] for m in resp.json()["messages"]}


def test_coach_message_filter_stays_in_scope(app: FastAPI, world: World) -> None:
    _message(app, world, 0, STUDY_A)
    want = _message(app, world, 1, STUDY_A)
    in_b = _message(app, world, 1, STUDY_B)
    flt = {"filter": "subtype=1"}
    assert _ids(world.client(app, "coach_in").get(M, params=flt)) == {want}
    # coach_other holds only B: the filter can neither widen to A nor hide scope.
    assert _ids(world.client(app, "coach_other").get(M, params=flt)) == {in_b}
    # With no in-scope record left, the same request is 404 (D-08 all removed).
    app.state.container.repositories.message().store[in_b].study_id = "study-c"
    assert world.client(app, "coach_other").get(M, params=flt).status_code == 404


def test_message_hostile_filter_after_scope(app: FastAPI, world: World) -> None:
    _message(app, world, 0, STUDY_A)
    assert (
        world.client(app, "coach_other").get(M, params={"filter": "owner=x"})
    ).status_code == 404
    assert (
        world.client(app, "owner_self").get(M, params={"filter": "owner=x"})
    ).status_code == 400
