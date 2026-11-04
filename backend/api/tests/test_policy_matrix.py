"""Behavior of the policy engine through real routes, generated from ``POLICY``.

``test_policy_matrix`` runs module x op x caller over every router that carries
an ``authorize`` dependency, so a plan that rolls a router onto the engine gains
coverage without editing this file. The named tests pin the decisions (D-06 to
D-08, D-16) on ``weight``, the reference router. ``body_for`` is shared with the
route-structure test.
"""

from __future__ import annotations

import types
import typing
from datetime import datetime
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from openwellness_api.auth.email_sender import FakeEmailSender
from openwellness_api.authz.engine import authorize
from openwellness_api.authz.policy import OPS, POLICY
from openwellness_api.resources import RESOURCE_MODULES
from openwellness_core.domain.exceptions.domain_exception import (
    EntityNotFoundException,
)
from openwellness_core.domain.models.participant import Participant
from openwellness_core.domain.models.weight import Weight

from .conftest import (
    STUDY_A,
    STUDY_B,
    World,
    make_fakes,
    reset_fakes,
    seed_world,
    token_for,
)
from .test_authz_engine import COACH_A, participants, run, stub_request

CALLERS = (
    "owner_self",
    "owner_other",
    "coach_in",
    "coach_other",
    "coach_empty",
    "admin",
    "no_role",
)
SUCCESS = {
    "create": 201,
    "get": 200,
    "list": 200,
    "patch": 200,
    "delete": 204,
    "undelete": 200,
    "purge": 204,
}
RANGE = {"startTime": "2026-01-01T00:00:00Z", "endTime": "2026-01-02T00:00:00Z"}
# condition ranges over integer weeks (parse_int), not timestamps.
INT_RANGE = {"startTime": 0, "endTime": 99999}
ZONE = {"name": "Cardio", "min": 1, "max": 2}

_BODY_OVERRIDES: dict[str, dict[str, Any]] = {
    "goal": {"kind": 0, "startDate": 1.0},
    "fitbit_heart_record": {
        "fitbitDate": "2026-01-01",
        "outOfRange": ZONE,
        "fatBurn": ZONE,
        "cardio": ZONE,
        "peak": ZONE,
    },
    "conversation": {"kind": 0, "owner": "x", "studyId": STUDY_A},
    "participant_group": {"participantIds": ["p-a"], "pidToMid": {}, "studyId": STUDY_A},
    "device": {"serialNumber": "x", "participantId": "p-a"},
    "fitbit": {"participantId": "p-a"},
}


def _module_name(mod: types.ModuleType) -> str:
    return mod.__name__.rsplit(".", 1)[-1]


def _rolled_out() -> list[str]:
    names = []
    for mod in RESOURCE_MODULES:
        deps = [
            d.call
            for route in mod.build_router().routes
            for d in getattr(route, "dependant").dependencies
        ]
        if any(isinstance(call, authorize) for call in deps):
            names.append(_module_name(mod))
    return names


ROLLED_OUT = _rolled_out()


# --------------------------------------------------------------------------- #
# Request bodies
# --------------------------------------------------------------------------- #


def _sample(annotation: Any) -> Any:
    origin = typing.get_origin(annotation)
    if origin in (typing.Union, types.UnionType):
        args = [a for a in typing.get_args(annotation) if a is not type(None)]
        return _sample(args[0])
    annotation = origin or annotation
    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            return {}
        if issubclass(annotation, bool):
            return True
        if issubclass(annotation, int):
            return 1
        if issubclass(annotation, float):
            return 1.0
        if issubclass(annotation, str):
            return "x"
        if issubclass(annotation, datetime):
            return "2026-01-01T00:00:00Z"
        if issubclass(annotation, dict):
            return {}
        if issubclass(annotation, (list, tuple, set)):
            return []
    return "x"


def body_for(module: str) -> dict[str, Any]:
    """A request body the module's create route accepts (plan 02-10 imports this)."""
    if module in _BODY_OVERRIDES:
        return _BODY_OVERRIDES[module]
    mod = next(m for m in RESOURCE_MODULES if _module_name(m) == module)
    router = mod.build_router()
    route = next(
        r
        for r in router.routes
        if "POST" in getattr(r, "methods", ()) and r.path == router.prefix  # type: ignore[attr-defined]
    )
    model = route.body_field.field_info.annotation  # type: ignore[attr-defined]
    return {
        (field.alias or name): _sample(field.annotation)
        for name, field in model.model_fields.items()
        if field.is_required()
    }


# --------------------------------------------------------------------------- #
# What the matrix expects
# --------------------------------------------------------------------------- #


def _cell(ops: frozenset[str], op: str) -> int:
    return SUCCESS[op] if op in ops else 403


def expected(module: str, op: str, caller: str) -> int:
    """Each module's ADR 0007 row for each caller class, under D-06 and D-07."""
    row = POLICY[module]
    record = op not in ("list", "create")
    if caller == "admin":
        return _cell(row.admin_ops, op)
    if module in ("admin", "app"):
        return 403
    own = _cell(row.self_ops, op)
    coach = _cell(row.coach_ops, op)
    is_coach = caller.startswith("coach")
    if module == "participant":
        if caller == "owner_self":
            return own
        if caller == "owner_other":
            return 404 if record else 403
        return coach if caller == "coach_in" else 404
    if module == "study":
        if caller == "owner_self":
            return own
        if caller == "owner_other":
            return 404 if record else 403
        if caller == "coach_in":
            return coach
        if caller == "no_role":
            return 404
        return 404 if record else coach
    if module == "user":
        if caller == "owner_self":
            return own
        if is_coach:
            return 403
        return 404 if record else 403
    if module in ("device", "fitbit"):
        if caller == "owner_self":
            return own
        if caller == "owner_other":
            if record:
                return 404
            return own if (module == "device" and op == "list") else 403
        return 403 if is_coach else 404
    if module == "conversation":
        if caller in ("owner_self", "owner_other"):
            if record:
                return 404
            return own if op == "list" else 403
        if caller == "coach_in":
            return coach
        if caller in ("coach_other", "coach_empty"):
            if record:
                return 404
            return coach if op == "list" else 404
        return 404
    # users/{user}/... rows, participant_group and the studies/{study}/... rows.
    if caller == "owner_self":
        return own
    return coach if caller == "coach_in" else 404


# --------------------------------------------------------------------------- #
# A shared app: building one takes ~0.35 s, a request ~2 ms.
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="module")
def matrix_app(app_builder: Any) -> Any:
    instance = app_builder(make_fakes(), FakeEmailSender())
    yield instance
    instance.state.container.unwire()


def _base(module: str) -> str:
    return POLICY[module].route.replace("{user}", "p-a").replace("{study}", STUDY_A)


_FIXED_IDS = {"user": "u-a", "study": STUDY_A, "participant": "p-a"}


def _seed_record(app: FastAPI, admin: TestClient, module: str) -> str:
    """One record for p-a in study A, created through the admin client."""
    if module in _FIXED_IDS:
        return _FIXED_IDS[module]
    resp = admin.post(_base(module), json=body_for(module))
    assert resp.status_code == 201 or module == "admin", resp.text
    store = getattr(app.state.container.repositories, module)().store
    return next(iter(store), "missing")


def _call(client: TestClient, module: str, op: str, rid: str) -> Any:
    base = _base(module)
    if op == "create":
        return client.post(base, json=body_for(module))
    if op == "list":
        return client.get(base, params=INT_RANGE if module == "condition" else RANGE)
    url = f"{base}/{rid}"
    if op == "get":
        return client.get(url)
    if op == "patch":
        return client.patch(url, json={})
    if op == "delete":
        return client.delete(url)
    return client.post(f"{url}:{op}")


_MATRIX = [(m, o, c) for m in ROLLED_OUT for o in OPS for c in CALLERS]


@pytest.mark.parametrize(
    ("module", "op", "caller"),
    _MATRIX,
    ids=[f"{m}-{o}-{c}" for m, o, c in _MATRIX],
)
def test_policy_matrix(matrix_app: FastAPI, module: str, op: str, caller: str) -> None:
    reset_fakes(matrix_app)
    world = seed_world(matrix_app)
    rid = _seed_record(matrix_app, world.client(matrix_app, "admin"), module)
    resp = _call(world.client(matrix_app, caller), module, op, rid)
    assert resp.status_code == expected(module, op, caller), resp.text


_CREATE_MODULES = [m for m in POLICY if m != "admin"]


@pytest.mark.parametrize("module", _CREATE_MODULES)
def test_body_for_creates_on_every_router(matrix_app: FastAPI, module: str) -> None:
    reset_fakes(matrix_app)
    world = seed_world(matrix_app)
    resp = world.client(matrix_app, "admin").post(_base(module), json=body_for(module))
    assert resp.status_code == 201, f"{module}: {resp.text}"


# --------------------------------------------------------------------------- #
# Named decisions, proven on weight
# --------------------------------------------------------------------------- #

W = "/v1/users/p-a/weights"


def _put_weight(app: FastAPI, id_: str, owner: str, study: str) -> None:
    app.state.container.repositories.weight().store[id_] = Weight(
        id=id_, owner=owner, study_id=study, weight=1.0
    )


def _names(resp: Any) -> list[str]:
    assert resp.status_code == 200, resp.text
    return [w["name"].rsplit("/", 1)[1] for w in resp.json()["weights"]]


def test_order_scope_before_role(app: FastAPI, world: World) -> None:
    _put_weight(app, "w1", "p-a", STUDY_A)
    me = world.client(app, "owner_self")
    assert me.post("/v1/users/p-b/weights", json={"weight": 1}).status_code == 404
    assert me.post(f"{W}/w1:purge").status_code == 403
    assert world.client(app, "coach_in").post(W, json={"weight": 1}).status_code == 403
    assert world.client(app, "coach_other").post(W, json={"weight": 1}).status_code == 404


def test_multirole_union(app: FastAPI, world: World) -> None:
    _put_weight(app, "mine", "p-d", STUDY_B)
    _put_weight(app, "theirs", "p-a", STUDY_A)
    dual = world.client(app, "dual")
    assert _names(dual.get("/v1/users/p-d/weights")) == ["mine"]
    assert _names(dual.get(W)) == ["theirs"]
    assert dual.post("/v1/users/p-d/weights/mine:purge").status_code == 403


def test_denial_404_matches_missing_404(app: FastAPI, world: World) -> None:
    _put_weight(app, "real-id", "p-a", STUDY_A)
    for caller in ("owner_other", "coach_other"):
        client = world.client(app, caller)
        denied = client.get(f"{W}/real-id")
        missing = client.get(f"{W}/gone-id")
        assert denied.status_code == missing.status_code == 404
        assert denied.text.replace("real-id", "ID") == missing.text.replace("gone-id", "ID")


def test_d08_all_removed_is_404(app: FastAPI, world: World) -> None:
    _put_weight(app, "a1", "p-a", STUDY_A)
    assert world.client(app, "coach_other").get(W).status_code == 404


def test_d08_mixed_returns_in_study_only(app: FastAPI, world: World) -> None:
    _put_weight(app, "a1", "p-a", STUDY_A)
    _put_weight(app, "b1", "p-a", STUDY_B)
    assert _names(world.client(app, "coach_in").get(W)) == ["a1"]
    assert _names(world.client(app, "coach_other").get(W)) == ["b1"]


def test_d08_past_study_record_visible_to_that_coach(app: FastAPI, world: World) -> None:
    _put_weight(app, "a1", "p-a", STUDY_A)
    app.state.container.repositories.participant().store["p-a"].study_id = STUDY_B
    assert _names(world.client(app, "coach_in").get(W)) == ["a1"]


def test_d08_no_records_is_empty_200(app: FastAPI, world: World) -> None:
    """The named AUTH-05 exception (A-02-1): empty 200, no data exposed."""
    resp = world.client(app, "coach_other").get(W)
    assert resp.status_code == 200, resp.text
    assert resp.json()["weights"] == []


def test_coach_scoped_list_pagination(app: FastAPI, world: World) -> None:
    for i in range(9):
        _put_weight(app, f"w{i}", "p-a", STUDY_A if i % 2 == 0 else STUDY_B)
    coach = world.client(app, "coach_in")
    seen: list[str] = []
    params: dict[str, Any] = {"page_size": 2}
    while True:
        resp = coach.get(W, params=params)
        seen += _names(resp)
        token = resp.json()["nextPageToken"]
        if not token:
            break
        params["page_token"] = token
    assert seen == ["w0", "w2", "w4", "w6", "w8"]


def test_study_id_compares_exactly(app: FastAPI, world: World) -> None:
    _put_weight(app, "a1", "p-a", STUDY_A)
    _put_weight(app, "none", "p-a", "")
    adjacent = TestClient(
        app,
        headers={
            "Authorization": "Bearer "
            + token_for(app, user_id="u-x", roles=["coach"], coach_studies=["study-a2"])
        },
    )
    assert adjacent.get(f"{W}/a1").status_code == 404
    assert world.client(app, "coach_in").get(f"{W}/none").status_code == 404
    assert world.client(app, "coach_both").get(f"{W}/none").status_code == 404


def test_study_binding(app: FastAPI, world: World) -> None:
    repo = app.state.container.repositories.participant()
    repo.store["p-nostudy"] = Participant(id="p-nostudy", study_id="")
    me = world.client(app, "owner_self")
    resp = me.post(W, json={"weight": 1})
    assert resp.status_code == 201 and resp.json()["studyId"] == STUDY_A
    assert me.post(W, json={"weight": 1, "studyId": STUDY_A}).status_code == 201
    forged = {"weight": 1, "studyId": STUDY_B}
    assert me.post(W, json=forged).status_code == 404
    admin = world.client(app, "admin")
    assert admin.post(W, json=forged).status_code == 404
    assert admin.post("/v1/users/p-nobody/weights", json={"weight": 1}).status_code == 404
    assert admin.post("/v1/users/p-nostudy/weights", json={"weight": 1}).status_code == 404
    # A coach with create on the row (the weight cell is read-only): engine level.
    people = participants(p_a=STUDY_A)
    request = stub_request("/v1/users/p-a/jobRules", {"user": "p-a"}, people)
    access = run("job_rule", "create", COACH_A, request)
    with pytest.raises(EntityNotFoundException):
        access.stamp_create({"study_id": STUDY_B}, parent_id="p-a")
    assert access.stamp_create({"study_id": ""}, parent_id="p-a")["study_id"] == STUDY_A


def test_updated_by_is_sub(app: FastAPI, world: World) -> None:
    me = world.client(app, "owner_self")
    forged = {"X-Principal-Id": "p-zzz"}
    created = me.post(W, json={"weight": 1}, headers=forged)
    assert created.status_code == 201 and created.json()["updatedBy"] == "u-a"
    wid = created.json()["name"].rsplit("/", 1)[1]
    patched = me.patch(f"{W}/{wid}", json={"weight": 2}, headers=forged)
    assert patched.status_code == 200 and patched.json()["updatedBy"] == "u-a"


@pytest.mark.parametrize("caller", ["owner_self", "admin"])
def test_patch_cannot_move_a_record(app: FastAPI, world: World, caller: str) -> None:
    _put_weight(app, "w1", "p-a", STUDY_A)
    body = {"weight": 5, "studyId": STUDY_B, "owner": "p-b", "updatedBy": "someone"}
    resp = world.client(app, caller).patch(f"{W}/w1", json=body)
    assert resp.status_code == 200, resp.text
    stored = app.state.container.repositories.weight().store["w1"]
    assert (stored.owner, stored.study_id, stored.weight) == ("p-a", STUDY_A, 5)
