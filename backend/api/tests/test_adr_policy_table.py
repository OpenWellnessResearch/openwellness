"""FOUND-07: every RESOURCE_MODULES entry has an ADR 0007 policy row; ADR index lists 0001-0007.

Reuses the 01-09 plan's inline check. Decision content is manual-only and is not tested here.
"""

from __future__ import annotations

import re
from pathlib import Path

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
