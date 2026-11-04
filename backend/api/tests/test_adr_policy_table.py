"""FOUND-07: every RESOURCE_MODULES entry has an ADR 0007 policy row; ADR index lists 0001-0007.

Reuses the 01-09 plan's inline check. Decision content is manual-only and is not tested here.
"""

from __future__ import annotations

import dataclasses
import re
from pathlib import Path

from openwellness_api.authz.policy import OPS, POLICY, Row
from openwellness_api.resources import RESOURCE_MODULES

ADR_DIR = Path(__file__).resolve().parents[3] / "docs" / "adr"
ROW = re.compile(r"^\|\s*`[a-z_]+`\s*\|")


def test_every_resource_module_has_a_policy_row() -> None:
    text = (ADR_DIR / "0007-authorization-policy-table.md").read_text(encoding="utf-8")
    rows = [
        line.strip().strip("|").split("|")[0].strip().strip("`")
        for line in text.splitlines()
        if ROW.match(line)
    ]
    want = sorted(m.__name__.rsplit(".", 1)[1] for m in RESOURCE_MODULES)
    assert len(rows) == 36
    assert sorted(rows) == want


def test_adr_index_lists_0001_through_0007_exactly_once() -> None:
    index = (ADR_DIR / "README.md").read_text(encoding="utf-8")
    files = sorted(p.name for p in ADR_DIR.glob("[0-9][0-9][0-9][0-9]-*.md"))
    assert [f[:4] for f in files] == [f"{n:04d}" for n in range(1, 8)]
    for name in files:
        assert index.count(f"({name})") == 1, name


BINDINGS = {
    "participant id": "participant",
    "study id": "study",
    "not routing-relevant (membership)": "membership",
}


def _cells(line: str) -> list[str]:
    return [c.strip().strip("`") for c in line.strip().strip("|").split("|")]


def _ops(cell: str) -> frozenset[str]:
    names = [] if cell == "none" else cell.split(",")
    return frozenset(c.strip() for c in names)


def _adr_rows(name: str) -> dict[str, list[str]]:
    text = (ADR_DIR / name).read_text(encoding="utf-8")
    return {_cells(l)[0]: _cells(l) for l in text.splitlines() if ROW.match(l)}


def _parse_0007(cells: list[str]) -> Row:
    _, route, scope, anonymous, self_ops, coach_ops, admin_ops = cells
    assert anonymous == "none"
    parts = [p.strip().strip("`") for p in scope.split(";")] if scope != "none" else []
    return Row(
        route=route,
        self_scope=next((p for p in parts if p.startswith("self-")), None),
        coach_scope=next((p for p in parts if p.startswith("coach-")), None),
        self_ops=_ops(self_ops),
        coach_ops=_ops(coach_ops),
        admin_ops=_ops(admin_ops),
        binding=None,
    )


def _row_diffs(adr: Row, py: Row) -> list[str]:
    """Differences per cell; binding is checked against ADR 0005, not ADR 0007."""
    return [
        f"{f.name}: adr={getattr(adr, f.name)!r} py={getattr(py, f.name)!r}"
        for f in dataclasses.fields(Row)
        if f.name != "binding" and getattr(adr, f.name) != getattr(py, f.name)
    ]


def test_policy_matches_adr_0007() -> None:
    diffs = []
    for module, cells in _adr_rows("0007-authorization-policy-table.md").items():
        if module not in POLICY:
            diffs.append(f"{module}: missing from POLICY")
            continue
        row_diffs = _row_diffs(_parse_0007(cells), POLICY[module])
        diffs += [f"{module} {d}" for d in row_diffs]
    assert diffs == []


def test_policy_row_diff_detects_a_changed_cell() -> None:
    adr = _parse_0007(_adr_rows("0007-authorization-policy-table.md")["weight"])
    assert _row_diffs(adr, adr) == []
    changed = dataclasses.replace(adr, self_ops=adr.self_ops - {"undelete"})
    assert len(_row_diffs(adr, changed)) == 1


def test_policy_keys_are_resource_modules() -> None:
    assert set(POLICY) == {m.__name__.rsplit(".", 1)[1] for m in RESOURCE_MODULES}


def test_only_admin_holds_purge() -> None:
    assert POLICY
    for module, row in POLICY.items():
        assert "purge" not in row.self_ops | row.coach_ops, module
        assert row.admin_ops == frozenset(OPS), module


def test_binding_matches_adr_0005() -> None:
    owner_holds = {
        module: BINDINGS[cells[2]]
        for module, cells in _adr_rows("0005-owner-semantics.md").items()
    }
    assert len(owner_holds) == 28
    assert {m: r.binding for m, r in POLICY.items()} == {
        m: owner_holds.get(m) for m in POLICY
    }
    assert set(POLICY) >= set(owner_holds)


AMENDMENT_LEADS = [
    "Scope before role (D-06).",
    "Multi-role union (D-07).",
    "Coach lists (D-08).",
    "Docs surface (D-09).",
    "Segment-less requests.",
    "Top-level lists.",
    "Patch keys.",
    "Custom methods.",
    "Staleness.",
    "Conversation membership.",
    "Archived records.",
    "Participant group lists.",
    "Empty out-of-study list (D-08).",
    "Group members.",
]


def test_phase_2_amendment_is_recorded() -> None:
    text = (ADR_DIR / "0007-authorization-policy-table.md").read_text(encoding="utf-8")
    assert text.count("\n## Phase 2 amendment\n") == 1
    for lead in AMENDMENT_LEADS:
        assert f"**{lead}**" in text, lead
    assert "D-06 refinement" in text
    assert len(_adr_rows("0007-authorization-policy-table.md")) == 36
