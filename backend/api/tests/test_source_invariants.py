"""FOUND-05 and FOUND-06: source-tree invariants checked with ast, not text search.

* No pymongo or bson import anywhere under backend/api/src.
* No print() call in the src trees of core, api and scheduler.
* No bare or broad except clause in mongo_base_repository.py.
"""

from __future__ import annotations

import ast
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
SRC_TREES = [
    BACKEND / "core" / "src",
    BACKEND / "api" / "src",
    BACKEND / "scheduler" / "src",
]
MONGO_BASE = (
    BACKEND
    / "core"
    / "src"
    / "openwellness_core"
    / "adapters"
    / "mongo"
    / "repositories"
    / "mongo_base_repository.py"
)
BROAD = {"Exception", "BaseException"}


def _parse(path: Path) -> ast.AST:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def test_api_source_imports_no_pymongo_or_bson() -> None:
    hits: list[str] = []
    for path in (BACKEND / "api" / "src").rglob("*.py"):
        for node in ast.walk(_parse(path)):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            else:
                continue
            hits += [f"{path}: {n}" for n in names if n.split(".")[0] in {"pymongo", "bson"}]
    assert hits == []


def test_no_print_call_in_core_api_or_scheduler_src() -> None:
    hits: list[str] = []
    for tree_root in SRC_TREES:
        for path in tree_root.rglob("*.py"):
            for node in ast.walk(_parse(path)):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "print"
                ):
                    hits.append(f"{path}:{node.lineno}")
    assert hits == []


def test_mongo_base_repository_has_no_bare_or_broad_except() -> None:
    hits: list[str] = []
    for node in ast.walk(_parse(MONGO_BASE)):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if node.type is None:
            hits.append(f"bare except at line {node.lineno}")
        elif isinstance(node.type, ast.Name) and node.type.id in BROAD:
            hits.append(f"except {node.type.id} at line {node.lineno}")
    assert hits == []


REMOVED_LITERALS = ("X-Principal-Id", "enforce_principal", "ENFORCE_PRINCIPAL", "require_principal")


def test_no_principal_header_or_permissive_mode_left() -> None:
    api = BACKEND / "api"
    files = [*(api / "src").rglob("*.py"), api / "README.md"]
    hits = [
        f"{path}: {lit}"
        for path in files
        for lit in REMOVED_LITERALS
        if lit in path.read_text(encoding="utf-8")
    ]
    assert hits == []


def test_env_example_turns_docs_on_with_a_warning() -> None:
    lines = (BACKEND.parent / ".env.example").read_text(encoding="utf-8").splitlines()
    assert "API_ENABLE_DOCS=true" in lines
    assert any("deployed instance" in line for line in lines)
