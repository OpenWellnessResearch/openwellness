"""Membership rows under the policy engine (AUTH-03, AUTH-05, AUTH-06, ADR 0005, ADR 0007).

``participant_group``: a participant reaches a group by membership, never by
owner, and a coach manages groups by the record's study. ``conversation`` follows
the same engine, with participants matching nothing until Phase 6.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI

from openwellness_core.domain.models.conversation import Conversation
from openwellness_core.domain.models.participant_group import ParticipantGroup

from .conftest import STUDY_A, STUDY_B, World

G = "/v1/users/{user}/participantGroups"


def _put_group(
    app: FastAPI,
    id_: str,
    *,
    owner: str = "p-a",
    study: str = STUDY_A,
    members: tuple[str, ...] = ("p-a",),
    created_at: float | None = None,
) -> ParticipantGroup:
    extra = {} if created_at is None else {"created_at": created_at}
    group = ParticipantGroup(
        id=id_,
        owner=owner,
        study_id=study,
        participant_ids=list(members),
        pid_to_mid={},
        **extra,
    )
    app.state.container.repositories.participant_group().store[id_] = group
    return group


def _ids(resp: Any) -> list[str]:
    assert resp.status_code == 200, resp.text
    return sorted(g["name"].rsplit("/", 1)[1] for g in resp.json()["participantGroups"])


def _body(study: str | None, members: list[str]) -> dict[str, Any]:
    body: dict[str, Any] = {"participantIds": members, "pidToMid": {}}
    if study is not None:
        body["studyId"] = study
    return body


# -- participant_group: participants -------------------------------------------


def test_member_reads_group(app: FastAPI, world: World) -> None:
    _put_group(app, "g1")
    resp = world.client(app, "owner_self").get(G.format(user="p-a") + "/g1")
    assert resp.status_code == 200, resp.text


def test_non_member_is_404_even_when_owner(app: FastAPI, world: World) -> None:
    _put_group(app, "g1", owner="p-a", members=("p-b",))
    me = world.client(app, "owner_self")
    assert me.get(G.format(user="p-a") + "/g1").status_code == 404
    assert _ids(me.get(G.format(user="p-a"))) == []


def test_other_segment_is_404(app: FastAPI, world: World) -> None:
    _put_group(app, "g1")
    resp = world.client(app, "owner_self").get(G.format(user="p-b") + "/g1")
    assert resp.status_code == 404


def test_member_list_returns_memberships_only(app: FastAPI, world: World) -> None:
    _put_group(app, "mine", owner="p-a", members=("p-a",))
    _put_group(app, "theirs", owner="p-x", members=("p-x", "p-a"))
    _put_group(app, "not-mine", owner="p-a", members=("p-b",))
    me = world.client(app, "owner_self")
    assert _ids(me.get(G.format(user="p-a"))) == ["mine", "theirs"]


def test_participant_cannot_write_group(app: FastAPI, world: World) -> None:
    _put_group(app, "g1")
    me = world.client(app, "owner_self")
    body = _body(STUDY_A, ["p-a"])
    assert me.post(G.format(user="p-a"), json=body).status_code == 403
    assert me.post(G.format(user="p-b"), json=body).status_code == 404
    assert me.patch(G.format(user="p-a") + "/g1", json={"info": {}}).status_code == 403


# -- participant_group: coaches ------------------------------------------------


def test_coach_group_scope_by_study(app: FastAPI, world: World) -> None:
    _put_group(app, "g1")
    url = G.format(user="p-zzz") + "/g1"
    coach = world.client(app, "coach_in")
    assert coach.get(url).status_code == 200
    assert coach.patch(url, json={"info": {"k": 1}}).status_code == 200
    other = world.client(app, "coach_other")
    assert other.get(url).status_code == 404
    assert other.patch(url, json={"info": {}}).status_code == 404


def test_coach_create_group_needs_held_study(app: FastAPI, world: World) -> None:
    url = G.format(user="p-a")
    coach = world.client(app, "coach_in")
    assert coach.post(url, json=_body(STUDY_A, ["p-a"])).status_code == 201
    assert coach.post(url, json=_body(STUDY_B, ["p-a"])).status_code == 404
    assert coach.post(url, json=_body(None, ["p-a"])).status_code == 404
    assert world.client(app, "admin").post(url, json=_body(None, ["p-a"])).status_code == 404


def test_group_list_time_range(app: FastAPI, world: World) -> None:
    _put_group(app, "old", created_at=1_000_000.0)  # 1970-01-12
    _put_group(app, "new", created_at=1_780_000_000.0)  # 2026
    me = world.client(app, "owner_self")
    window = {"startTime": "2026-01-01T00:00:00Z", "endTime": "2027-01-01T00:00:00Z"}
    assert _ids(me.get(G.format(user="p-a"), params=window)) == ["new"]
    assert _ids(me.get(G.format(user="p-a"))) == ["new", "old"]


# -- participant_group: A-09-2 members ----------------------------------------


def test_coach_group_create_cross_study_member_is_404(
    app: FastAPI, world: World
) -> None:
    url = G.format(user="p-a")
    store = app.state.container.repositories.participant_group().store
    coach = world.client(app, "coach_in")
    cross = coach.post(url, json=_body(STUDY_A, ["p-a", "p-b"]))
    assert cross.status_code == 404
    assert not store
    wrong_study = coach.post(url, json=_body(STUDY_B, ["p-a"]))
    unknown = coach.post(url, json=_body(STUDY_A, ["p-a", "p-nobody"]))
    assert wrong_study.status_code == unknown.status_code == 404
    assert cross.text == wrong_study.text == unknown.text
    assert not store


def test_coach_group_patch_cross_study_member_is_404(
    app: FastAPI, world: World
) -> None:
    group = _put_group(app, "g1")
    url = G.format(user="p-a") + "/g1"
    resp = world.client(app, "coach_in").patch(url, json={"participantIds": ["p-a", "p-b"]})
    assert resp.status_code == 404
    assert group.participant_ids == ["p-a"]
    denied = world.client(app, "coach_other").patch(url, json={"participantIds": ["p-a"]})
    assert denied.status_code == 404
    assert resp.text == denied.text


def test_admin_group_members_unrestricted(app: FastAPI, world: World) -> None:
    _put_group(app, "g1")
    admin = world.client(app, "admin")
    created = admin.post(G.format(user="p-a"), json=_body(STUDY_A, ["p-a", "p-b"]))
    assert created.status_code == 201, created.text
    patched = admin.patch(
        G.format(user="p-a") + "/g1", json={"participantIds": ["p-a", "p-b"]}
    )
    assert patched.status_code == 200, patched.text


def test_coach_group_patch_without_members_reads_no_participant(
    app: FastAPI, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    _put_group(app, "g1", members=("p-a", "p-b"))

    def boom(*_: Any, **__: Any) -> Any:
        raise AssertionError("a patch without participantIds must not read Participant")

    monkeypatch.setattr(app.state.container.repositories.participant(), "get_by_id", boom)
    resp = world.client(app, "coach_in").patch(
        G.format(user="p-a") + "/g1", json={"info": {"k": 1}}
    )
    assert resp.status_code == 200, resp.text


# -- conversation --------------------------------------------------------------

C = "/v1/conversations"


def _put_conversation(
    app: FastAPI, id_: str, *, study: str = STUDY_A, owner: str = "p-a", kind: int = 0
) -> Conversation:
    conversation = Conversation(id=id_, kind=kind, owner=owner, study_id=study)
    app.state.container.repositories.conversation().store[id_] = conversation
    return conversation


def _conversation_ids(resp: Any) -> list[str]:
    assert resp.status_code == 200, resp.text
    return sorted(c["name"].rsplit("/", 1)[1] for c in resp.json()["conversations"])


def test_participant_matches_no_conversation(app: FastAPI, world: World) -> None:
    _put_conversation(app, "c1", owner="p-a")
    for caller in ("owner_self", "owner_other"):
        me = world.client(app, caller)
        assert me.get(f"{C}/c1").status_code == 404
        assert _conversation_ids(me.get(C)) == []
        searched = me.post(f"{C}:search", json={"filters": []})
        assert _conversation_ids(searched) == []
    body = {"kind": 0, "owner": "p-a", "studyId": STUDY_A}
    assert world.client(app, "owner_self").post(C, json=body).status_code == 403


def test_coach_conversation_scope(app: FastAPI, world: World) -> None:
    _put_conversation(app, "ca", study=STUDY_A)
    _put_conversation(app, "cb", study=STUDY_B)
    coach = world.client(app, "coach_in")
    assert coach.get(f"{C}/ca").status_code == 200
    assert coach.get(f"{C}/cb").status_code == 404
    assert _conversation_ids(coach.get(C)) == ["ca"]
    other = world.client(app, "coach_other")
    assert other.get(f"{C}/ca").status_code == 404
    assert _conversation_ids(other.get(C)) == ["cb"]
    empty = world.client(app, "coach_empty")
    assert _conversation_ids(empty.get(C)) == []
    # Both studies match the filter; scope runs after it and cannot be widened.
    match_all = {"filters": [{"type": "kind", "val": 0}]}
    assert _conversation_ids(coach.post(f"{C}:search", json=match_all)) == ["ca"]


def test_coach_create_conversation_needs_held_study(app: FastAPI, world: World) -> None:
    coach = world.client(app, "coach_in")
    body: dict[str, Any] = {"kind": 0, "owner": "p-a"}
    assert coach.post(C, json={**body, "studyId": STUDY_A}).status_code == 201
    assert coach.post(C, json={**body, "studyId": STUDY_B}).status_code == 404
    assert coach.post(C, json=body).status_code == 404


def test_conversation_updated_by_from_token(app: FastAPI, world: World) -> None:
    resp = world.client(app, "coach_in").post(
        C, json={"kind": 0, "owner": "p-a", "studyId": STUDY_A}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["updatedBy"] == "u-ci"
    assert resp.json()["owner"] == "p-a"


def test_conversation_patch_cannot_move(app: FastAPI, world: World) -> None:
    stored = _put_conversation(app, "c1", study=STUDY_A, owner="p-a")
    resp = world.client(app, "coach_in").patch(
        f"{C}/c1", json={"title": "t", "studyId": STUDY_B, "owner": "p-b"}
    )
    assert resp.status_code == 200, resp.text
    assert (stored.study_id, stored.owner, stored.title) == (STUDY_A, "p-a", "t")
