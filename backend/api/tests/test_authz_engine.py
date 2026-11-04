"""The decision function in isolation: ``authorize`` against a stub request.

The stub carries only what the engine reads: ``path_params``, ``url.path`` and
the Participant repository reachable through ``app.state.container``.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import HTTPException

from openwellness_api.authz.engine import Access, authorize
from openwellness_api.authz.policy import OPS, POLICY
from openwellness_api.deps.principal import Principal

from .conftest import InMemoryBaseRepo


def stub_request(
    path: str,
    params: dict[str, str] | None = None,
    participants: InMemoryBaseRepo | None = None,
) -> Any:
    repo = participants if participants is not None else InMemoryBaseRepo()
    container = SimpleNamespace(
        repositories=SimpleNamespace(participant=lambda: repo)
    )
    return SimpleNamespace(
        path_params=params or {},
        url=SimpleNamespace(path=path),
        app=SimpleNamespace(state=SimpleNamespace(container=container)),
    )


def run(
    module: str, op: str, principal: Principal, request: Any
) -> Access:
    return authorize(module, op)(request, principal)


@pytest.mark.parametrize(
    ("module", "op"), [("nope", "get"), ("weight", "frobnicate")]
)
def test_unknown_module_or_op_is_denied_403(module: str, op: str) -> None:
    with pytest.raises(HTTPException) as exc:
        run(module, op, Principal(id="u", roles=("admin",)), stub_request("/v1/x"))
    assert exc.value.status_code == 403


# --------------------------------------------------------------------------- #
# The decision table. ``decide`` runs authorize, then check_record when a record
# is given, and reports "allow", 403 or 404.
# --------------------------------------------------------------------------- #

SELF_A = Principal(id="u-a", roles=("participant",), participant="p-a")
COACH_A = Principal(id="u-c", roles=("coach",), coach_studies=("study-a",))
COACH_NONE = Principal(id="u-c0", roles=("coach",))
ADMIN = Principal(id="u-adm", roles=("admin",))
NO_ROLE = Principal(id="u-n")


def participants(**study_by_pid: Any) -> InMemoryBaseRepo:
    repo = InMemoryBaseRepo()
    for pid, study in study_by_pid.items():
        if isinstance(study, str):
            study = SimpleNamespace(id=pid, study_id=study)
        repo.store[pid.replace("_", "-")] = study
    return repo


def rec(**fields: Any) -> Any:
    return SimpleNamespace(**fields)


def decide(
    module: str,
    op: str,
    principal: Principal,
    path: str,
    params: dict[str, str] | None = None,
    record: Any = None,
    people: InMemoryBaseRepo | None = None,
    name: str | None = None,
) -> Any:
    from openwellness_core.domain.exceptions.domain_exception import (
        EntityNotFoundException,
    )

    request = stub_request(path, params, people)
    try:
        access = run(module, op, principal, request)
        if record is not None:
            access.check_record(record, name=name)
    except HTTPException as exc:
        return exc.status_code
    except EntityNotFoundException:
        return 404
    return "allow"


PEOPLE = participants(p_a="study-a", p_b="study-b")
W = "/v1/users/p-a/weights/w"
CASES = [
    # self-user: {user} equals sub; no segment is vacuous
    ("user", "get", SELF_A, "/v1/users/u-a", {"user": "u-a"}, None, "allow"),
    ("user", "get", SELF_A, "/v1/users/u-x", {"user": "u-x"}, None, 404),
    ("user", "list", SELF_A, "/v1/users", {}, None, 403),
    # self-owner: {user} equals the participant claim; an empty claim is False
    ("weight", "get", SELF_A, W, {"user": "p-a"}, None, "allow"),
    ("weight", "get", SELF_A, W, {"user": "p-b"}, None, 404),
    ("weight", "purge", SELF_A, W, {"user": "p-a"}, None, 403),
    ("weight", "get", NO_ROLE, W, {"user": "p-a"}, None, 404),
    # self-participant
    ("participant", "get", SELF_A, "/v1/studies/study-a/participants/p-a",
     {"study": "study-a", "participant": "p-a"}, None, "allow"),
    ("participant", "get", SELF_A, "/v1/studies/study-a/participants/p-b",
     {"study": "study-a", "participant": "p-b"}, None, 404),
    ("participant", "list", SELF_A, "/v1/studies/study-b/participants",
     {"study": "study-b"}, None, 403),
    ("participant", "create", SELF_A, "/v1/studies/study-a/participants",
     {"study": "study-a"}, None, 403),
    # self-study: segment, no segment, record, fail closed
    ("study_message", "list", SELF_A, "/v1/studies/study-a/studyMessages",
     {"study": "study-a"}, None, "allow"),
    ("study_message", "list", SELF_A, "/v1/studies/study-b/studyMessages",
     {"study": "study-b"}, None, 404),
    ("study", "get", SELF_A, "/v1/studies/study-a", {"study": "study-a"}, None, "allow"),
    ("study", "list", SELF_A, "/v1/studies", {}, None, 403),
    ("study", "get", SELF_A, "/v1/studies:lookup", {}, rec(id="study-a"), "allow"),
    ("study", "get", SELF_A, "/v1/studies:lookup", {}, rec(id="study-b"), 404),
    # self-device, self-fitbit
    ("device", "get", SELF_A, "/v1/devices/d", {"device": "d"},
     rec(participant_id="p-a"), "allow"),
    ("device", "get", SELF_A, "/v1/devices/d", {"device": "d"},
     rec(participant_id="p-b"), 404),
    ("device", "list", SELF_A, "/v1/devices", {}, None, "allow"),
    ("device", "create", SELF_A, "/v1/devices", {}, None, 403),
    ("fitbit", "get", SELF_A, "/v1/fitbits/f", {"fitbit": "f"},
     rec(participant_id="p-a"), "allow"),
    ("fitbit", "list", SELF_A, "/v1/fitbits", {}, None, 403),
    # self-member-group: segment must be the claim, claim in participant_ids
    ("participant_group", "get", SELF_A, "/v1/users/p-a/participantGroups/g",
     {"user": "p-a"}, rec(participant_ids=["p-a"]), "allow"),
    ("participant_group", "get", SELF_A, "/v1/users/p-a/participantGroups/g",
     {"user": "p-a"}, rec(participant_ids=["p-b"]), 404),
    ("participant_group", "get", SELF_A, "/v1/users/p-a/participantGroups/g",
     {"user": "p-a"}, rec(participant_ids=["p-a"], deleted_at=1.0), 404),
    ("participant_group", "get", SELF_A, "/v1/users/p-b/participantGroups/g",
     {"user": "p-b"}, rec(participant_ids=["p-a"]), 404),
    ("participant_group", "list", SELF_A, "/v1/users/p-a/participantGroups",
     {"user": "p-a"}, None, "allow"),
    ("participant_group", "create", SELF_A, "/v1/users/p-a/participantGroups",
     {"user": "p-a"}, None, 403),
    # self-member-conversation matches nothing (OQ1)
    ("conversation", "get", SELF_A, "/v1/conversations/c", {"conversation": "c"},
     rec(study_id="study-a"), 404),
    ("conversation", "create", SELF_A, "/v1/conversations", {}, None, 403),
    # coach-study: {study} segment, study row, binding participant, membership
    ("participant", "get", COACH_A, "/v1/studies/study-a/participants/p-a",
     {"study": "study-a", "participant": "p-a"}, None, "allow"),
    ("participant", "get", COACH_A, "/v1/studies/study-b/participants/p-b",
     {"study": "study-b", "participant": "p-b"}, None, 404),
    ("study", "get", COACH_A, "/v1/studies:lookup", {}, rec(id="study-a"), "allow"),
    ("study", "get", COACH_A, "/v1/studies:lookup", {}, rec(id="study-b"), 404),
    ("study", "create", COACH_A, "/v1/studies", {}, None, 403),
    ("job_rule", "create", COACH_A, "/v1/users/p-a/jobRules", {"user": "p-a"}, None, "allow"),
    ("job_rule", "create", COACH_A, "/v1/users/p-b/jobRules", {"user": "p-b"}, None, 404),
    ("job_rule", "create", COACH_NONE, "/v1/users/p-a/jobRules", {"user": "p-a"}, None, 404),
    ("weight", "get", COACH_A, W, {"user": "p-a"}, rec(study_id="study-a", owner="p-a"), "allow"),
    ("weight", "get", COACH_A, W, {"user": "p-a"}, rec(study_id="study-b", owner="p-a"), 404),
    ("weight", "get", COACH_A, W, {"user": "p-a"}, rec(study_id="", owner="p-a"), 404),
    ("weight", "get", COACH_A, W, {"user": "p-a"}, rec(study_id="study-a2", owner="p-a"), 404),
    ("weight", "purge", COACH_A, W, {"user": "p-a"}, rec(study_id="study-a", owner="p-a"), 403),
    ("conversation", "create", COACH_A, "/v1/conversations", {}, None, "allow"),
    ("conversation", "get", COACH_A, "/v1/conversations/c", {"conversation": "c"},
     rec(study_id="study-a"), "allow"),
    ("conversation", "get", COACH_A, "/v1/conversations/c", {"conversation": "c"},
     rec(study_id="study-b"), 404),
    # admin has no predicate
    ("weight", "purge", ADMIN, W, {"user": "p-a"}, None, "allow"),
]


@pytest.mark.parametrize(
    ("module", "op", "principal", "path", "params", "record", "expected"),
    CASES,
    ids=[f"{c[0]}-{c[1]}-{i}" for i, c in enumerate(CASES)],
)
def test_decision_table(
    module: str, op: str, principal: Principal, path: str,
    params: dict[str, str], record: Any, expected: Any,
) -> None:
    assert decide(module, op, principal, path, params, record, PEOPLE) == expected


@pytest.mark.parametrize(
    "people",
    [
        participants(),  # no Participant record
        participants(p_a=""),  # empty study_id
        participants(p_a=SimpleNamespace(id="p-a", study_id="study-a", deleted_at=1.0)),
    ],
    ids=["missing", "empty-study", "archived"],
)
def test_own_study_fails_closed(people: InMemoryBaseRepo) -> None:
    path = "/v1/studies/study-a/studyMessages"
    assert decide("study_message", "list", SELF_A, path, {"study": "study-a"}, None, people) == 404


@pytest.mark.parametrize(
    ("module", "path", "params"),
    [
        ("device", "/v1/devices/d", {"device": "d"}),
        ("fitbit", "/v1/fitbits/f", {"fitbit": "f"}),
        ("user", "/v1/users/u-x", {"user": "u-x"}),
    ],
)
def test_role_predicate_precedes_scope_none(
    module: str, path: str, params: dict[str, str]
) -> None:
    """A column exists only for a held role: no role is 404, a coach is 403."""
    for op in ("get", "patch", "delete", "undelete", "purge"):
        record = rec(participant_id="p-a")
        assert decide(module, op, NO_ROLE, path, params, record, PEOPLE) == 404, op
        assert decide(module, op, COACH_A, path, params, record, PEOPLE) == 403, op


@pytest.mark.parametrize("module", ["admin", "app"])
def test_admin_and_app_are_403_for_every_non_admin(module: str) -> None:
    for principal in (NO_ROLE, SELF_A, COACH_A):
        for op in OPS:
            assert decide(module, op, principal, f"/v1/{module}s/x", {}, None, PEOPLE) == 403
    assert decide(module, "purge", ADMIN, f"/v1/{module}s/x", {}, None, PEOPLE) == "allow"


def test_stamp_create_refuses_a_row_with_no_binding() -> None:
    unbound = [m for m, row in POLICY.items() if row.binding is None]
    assert len(unbound) == 8
    for module in unbound:
        access = run(module, "create", ADMIN, stub_request(f"/v1/{module}s"))
        with pytest.raises(ValueError, match=module):
            access.stamp_create({}, parent_id=None)


def test_coach_write_check() -> None:
    """A record in study A whose owner has moved to study B is 404 for a coach write."""
    path = "/v1/users/p-a/jobRules/j"
    record = rec(study_id="study-a", owner="p-a")
    moved = participants(p_a="study-b")
    stayed = participants(p_a="study-a")
    for op in ("patch", "delete", "undelete"):
        assert decide("job_rule", op, COACH_A, path, {"user": "p-a"}, record, moved) == 404
        assert decide("job_rule", op, COACH_A, path, {"user": "p-a"}, record, stayed) == "allow"
    # A read needs no owner lookup.
    assert decide("job_rule", "get", COACH_A, path, {"user": "p-a"}, record, moved) == "allow"


def test_check_record_name_sets_the_404_text() -> None:
    from openwellness_api.common.handlers import not_found
    from openwellness_core.domain.exceptions.domain_exception import (
        EntityNotFoundException,
    )

    with pytest.raises(EntityNotFoundException) as expected:
        not_found("studies", "n")
    access = run("study", "get", SELF_A, stub_request("/v1/studies:lookup", {}, PEOPLE))
    with pytest.raises(EntityNotFoundException) as named:
        access.check_record(rec(id="study-b"), name="n")
    assert named.value.message == expected.value.message
    with pytest.raises(EntityNotFoundException) as derived:
        access.check_record(rec(id="study-b"))
    assert derived.value.message == "studies not found"


class _CountingRepo(InMemoryBaseRepo):
    reads = 0

    def get_by_id(self, entity_id: str) -> Any | None:
        _CountingRepo.reads += 1
        return super().get_by_id(entity_id)


def _members_access(principal: Principal, repo: InMemoryBaseRepo) -> Access:
    request = stub_request("/v1/users/p-a/participantGroups", {"user": "p-a"}, repo)
    return run("participant_group", "create", principal, request)


def test_check_members() -> None:
    from openwellness_core.domain.exceptions.domain_exception import (
        EntityNotFoundException,
    )

    counting = _CountingRepo()
    _members_access(ADMIN, counting).check_members(["anyone"])
    assert _CountingRepo.reads == 0

    people = participants(
        p_a="study-a",
        p_b="study-b",
        p_e="",
        p_x=SimpleNamespace(id="p-x", study_id="study-a", deleted_at=1.0),
    )
    coach = _members_access(COACH_A, people)
    coach.check_members([])
    coach.check_members(["p-a"])
    texts = set()
    for bad in ("p-b", "p-unknown", "p-x", "p-e"):
        with pytest.raises(EntityNotFoundException) as exc:
            _members_access(COACH_A, people).check_members(["p-a", bad])
        texts.add(exc.value.message)
    assert texts == {"participantGroups not found for users/p-a"}
