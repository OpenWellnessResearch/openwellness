"""The authorization policy as data, one row per resource module.

Mirrors ADR 0007 (Policy table) and the owner binding of ADR 0005. It is checked
against both by ``tests/test_adr_policy_table.py`` and never built from them at
runtime: the API does not read the ADR files.
"""

from __future__ import annotations

from dataclasses import dataclass

OPS = ("get", "list", "create", "patch", "delete", "undelete", "purge")

# Custom methods that reuse a table op (assumption A4, developer-confirmed).
CUSTOM_OPS = {"conversation": {"search": "list"}, "study": {"lookup": "get"}}


@dataclass(frozen=True)
class Row:
    route: str
    self_scope: str | None
    coach_scope: str | None
    self_ops: frozenset[str]
    coach_ops: frozenset[str]
    admin_ops: frozenset[str]
    # What ADR 0005 says `owner` holds: "participant", "study" or "membership".
    binding: str | None


POLICY: dict[str, Row] = {}
