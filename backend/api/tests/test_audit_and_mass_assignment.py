"""AUTH-06 and the ADR 0007 mass-assignment caveat, swept across every owner-bound row.

Parametrized from ``POLICY``: a module qualifies by its ``binding`` and a caller
by the policy cell for the op, so a new owner-scoped row is covered without
editing this file. The single-row proofs live in plans 02-04, 02-06 and 02-07.
"""

from __future__ import annotations

from typing import Any

import jwt
import pytest
from fastapi import FastAPI

from openwellness_api.auth.email_sender import FakeEmailSender
from openwellness_api.authz.policy import POLICY

from .conftest import STUDY_B, make_fakes, reset_fakes, seed_world
from .test_policy_matrix import CALLERS, _base, _seed_record, body_for, expected

BOUND = [m for m, row in POLICY.items() if row.binding is not None]
PARTICIPANT_BOUND = [m for m, row in POLICY.items() if row.binding == "participant"]
FORGED = {"X-Principal-Id": "p-zzz"}


def _allowed(modules: list[str], op: str) -> list[tuple[str, str]]:
    return [(m, c) for m in modules for c in CALLERS if expected(m, op, c) in (200, 201)]


@pytest.fixture(scope="module")
def sweep_app(app_builder: Any) -> FastAPI:
    instance = app_builder(make_fakes(), FakeEmailSender())
    yield instance
    instance.state.container.unwire()


def _sub(world: Any, caller: str) -> str:
    token = world.headers[caller]["Authorization"].split(" ", 1)[1]
    return jwt.decode(token, options={"verify_signature": False})["sub"]


def _stored(app: FastAPI, module: str, rid: str | None = None) -> Any:
    store = getattr(app.state.container.repositories, module)().store
    return store[rid] if rid else list(store.values())[-1]


@pytest.mark.parametrize(("module", "caller"), _allowed(BOUND, "create"))
def test_forged_header_ignored_on_create(sweep_app: FastAPI, module: str, caller: str) -> None:
    reset_fakes(sweep_app)
    world = seed_world(sweep_app)
    resp = world.client(sweep_app, caller).post(
        _base(module), json=body_for(module), headers=FORGED
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["updatedBy"] == _sub(world, caller)
    assert _stored(sweep_app, module).updated_by == _sub(world, caller)


@pytest.mark.parametrize(("module", "caller"), _allowed(BOUND, "patch"))
def test_forged_header_ignored_on_patch(sweep_app: FastAPI, module: str, caller: str) -> None:
    reset_fakes(sweep_app)
    world = seed_world(sweep_app)
    rid = _seed_record(sweep_app, world.client(sweep_app, "admin"), module)
    resp = world.client(sweep_app, caller).patch(
        f"{_base(module)}/{rid}", json={}, headers=FORGED
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["updatedBy"] == _sub(world, caller)
    assert _stored(sweep_app, module, rid).updated_by == _sub(world, caller)


@pytest.mark.parametrize("module", [m for m in PARTICIPANT_BOUND if expected(m, "create", "owner_self") == 201])
def test_updated_by_is_sub_not_participant(sweep_app: FastAPI, module: str) -> None:
    reset_fakes(sweep_app)
    world = seed_world(sweep_app)
    resp = world.client(sweep_app, "owner_self").post(_base(module), json=body_for(module))
    assert resp.status_code == 201, resp.text
    stored = _stored(sweep_app, module).updated_by
    assert stored == "u-a"
    assert stored != "p-a"  # D-16: the account id, not the participant id


MOVE = {
    "owner": "p-b",
    "studyId": STUDY_B,
    "updatedBy": "forged",
    "createTime": "2001-01-01T00:00:00Z",
    "updateTime": "2001-01-01T00:00:00Z",
}


@pytest.mark.parametrize("module", BOUND)
def test_patch_cannot_move_record_any_row(sweep_app: FastAPI, module: str) -> None:
    reset_fakes(sweep_app)
    world = seed_world(sweep_app)
    admin = world.client(sweep_app, "admin")
    rid = _seed_record(sweep_app, admin, module)
    before = _stored(sweep_app, module, rid)
    snapshot = {k: getattr(before, k, None) for k in ("owner", "study_id", "created_at")}
    resp = admin.patch(f"{_base(module)}/{rid}", json=MOVE)
    assert resp.status_code == 200, resp.text
    after = _stored(sweep_app, module, rid)
    assert {k: getattr(after, k, None) for k in snapshot} == snapshot
    assert after.updated_by == _sub(world, "admin")


@pytest.mark.parametrize("module", PARTICIPANT_BOUND)
def test_create_refuses_differing_study_any_row(sweep_app: FastAPI, module: str) -> None:
    reset_fakes(sweep_app)
    world = seed_world(sweep_app)
    body = {**body_for(module), "studyId": STUDY_B}  # p-a is enrolled in study A
    resp = world.client(sweep_app, "admin").post(_base(module), json=body)
    assert resp.status_code == 404, resp.text


@pytest.mark.parametrize("module", PARTICIPANT_BOUND)
def test_create_needs_owner_participant_any_row(sweep_app: FastAPI, module: str) -> None:
    reset_fakes(sweep_app)
    world = seed_world(sweep_app)
    url = POLICY[module].route.replace("{user}", "p-nobody")
    resp = world.client(sweep_app, "admin").post(url, json=body_for(module))
    assert resp.status_code == 404, resp.text
