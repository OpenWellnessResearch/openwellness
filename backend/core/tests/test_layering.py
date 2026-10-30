"""FOUND-04: domain and application stay free of datastore, framework and adapter imports.

Walks every source file under openwellness_core.domain and
openwellness_core.application with ast (relative imports are resolved to
absolute module names first), so text such as comments or strings cannot
produce false results.
"""

from __future__ import annotations

import ast
from pathlib import Path

CORE_SRC = Path(__file__).resolve().parents[1] / "src" / "openwellness_core"
LAYERS = [CORE_SRC / "domain", CORE_SRC / "application"]
FORBIDDEN_THIRD_PARTY = {
    "bson",
    "pymongo",
    "couchbase",
    "redis",
    "celery",
    "fastapi",
    "sqlalchemy",
    "psycopg",
}
FORBIDDEN_INTERNAL = ("openwellness_core.adapters", "openwellness_core.infrastructure")


def _resolve(path: Path, node: ast.ImportFrom) -> str:
    """Return the absolute dotted module name an ImportFrom refers to."""
    if node.level == 0:
        return node.module or ""
    parts = list(path.relative_to(CORE_SRC.parent).with_suffix("").parts)
    package = parts if path.name == "__init__.py" else parts[:-1]
    base = package[: len(package) - (node.level - 1)]
    return ".".join(base + ([node.module] if node.module else []))


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_THIRD_PARTY:
                    found.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            target = _resolve(path, node)
            if node.level == 0 and target.split(".")[0] in FORBIDDEN_THIRD_PARTY:
                found.append(target)
            if target.startswith(FORBIDDEN_INTERNAL):
                found.append(target)
            if target == "openwellness_core":
                for alias in node.names:
                    if alias.name in {"adapters", "infrastructure"}:
                        found.append(f"openwellness_core.{alias.name}")
    return found


def test_domain_and_application_import_no_datastore_framework_or_outer_layer() -> None:
    files = [p for layer in LAYERS for p in layer.rglob("*.py")]
    assert files, "layering walk found no source files; the check would be vacuous"
    failures = {
        str(p.relative_to(CORE_SRC)): v
        for p in files
        if (v := _violations(p))
    }
    assert failures == {}
