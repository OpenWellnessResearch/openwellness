"""``filter=`` only narrows: scope runs first and the grammar cannot name owner or study.

Goal is the one participant-data row with a filter (D-08, AUTH-03): a coach's
study scope applies to the unfiltered owner list, and a hostile filter on
another participant's path is 404, never 400.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from .conftest import STUDY_A, STUDY_B, World

G = "/v1/users/p-a/goals"


def _goal(app: FastAPI, world: World, kind: int, study: str) -> str:
    """Create a goal under p-a as admin, then pin its study (the owner's is A)."""
    resp = world.client(app, "admin").post(G, json={"kind": kind, "startDate": 1.0})
    assert resp.status_code == 201, resp.text
    id_ = resp.json()["name"].rsplit("/", 1)[1]
    app.state.container.repositories.goal().store[id_].study_id = study
    return id_


def _ids(resp: Any) -> set[str]:
    assert resp.status_code == 200, resp.text
    return {g["name"].rsplit("/", 1)[1] for g in resp.json()["goals"]}


def test_owner_filter_on_own_path_is_400(app: FastAPI, world: World) -> None:
    _goal(app, world, 0, STUDY_A)
    resp = world.client(app, "owner_self").get(G, params={"filter": "owner=p-b"})
    assert resp.status_code == 400
    assert resp.json()["error"]["status"] == "INVALID_ARGUMENT"


def test_owner_filter_on_other_path_is_404(app: FastAPI, world: World) -> None:
    _goal(app, world, 1, STUDY_A)
    other = world.client(app, "owner_other")
    for flt in ("kind=1", "owner=p-b"):
        assert other.get(G, params={"filter": flt}).status_code == 404, flt


def test_kind_filter_on_other_path_is_404(app: FastAPI, world: World) -> None:
    id_ = _goal(app, world, 1, STUDY_B)
    resp = world.client(app, "owner_self").get(
        "/v1/users/p-b/goals", params={"filter": "kind=1"}
    )
    assert resp.status_code == 404
    assert id_ not in resp.text


def test_coach_kind_filter_stays_in_scope(app: FastAPI, world: World) -> None:
    _goal(app, world, 0, STUDY_A)
    want = _goal(app, world, 1, STUDY_A)
    _goal(app, world, 1, STUDY_B)
    _goal(app, world, 0, STUDY_B)
    resp = world.client(app, "coach_in").get(G, params={"filter": "kind=1"})
    assert _ids(resp) == {want}


def test_coach_kind_filter_all_removed_is_404(app: FastAPI, world: World) -> None:
    _goal(app, world, 0, STUDY_A)
    resp = world.client(app, "coach_other").get(G, params={"filter": "kind=1"})
    assert resp.status_code == 404


def test_hostile_filter_after_scope(app: FastAPI, world: World) -> None:
    _goal(app, world, 0, STUDY_A)
    resp = world.client(app, "coach_other").get(G, params={"filter": "weight=10"})
    assert resp.status_code == 404
