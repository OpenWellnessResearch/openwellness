"""Helpers for safely assembling N1QL queries.

N1QL placeholders (``$name``) cannot stand in for identifiers — only values.
So column names, ORDER BY targets, and similar must be validated against a
per-repository allowlist before they're spliced into the query string. The
bucket name comes from trusted config but is wrapped in backticks for
robustness against hyphens.
"""

from __future__ import annotations


def allowed_column(name: str, allowed: frozenset[str]) -> str:
    """Return ``name`` if it is in ``allowed``; otherwise raise ``ValueError``.

    Use this whenever a caller-controlled string is interpolated as an
    identifier (e.g. ``ORDER BY {col}``). Identifiers cannot be parameterized
    in N1QL, so the only safe path is an allowlist.
    """
    if name not in allowed:
        raise ValueError(f"unknown column: {name!r}")
    return name


def bucket_ident(bucket: str) -> str:
    """Wrap a bucket name in backticks for safe interpolation into N1QL."""
    return f"`{bucket}`"
