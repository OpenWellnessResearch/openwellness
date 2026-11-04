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
