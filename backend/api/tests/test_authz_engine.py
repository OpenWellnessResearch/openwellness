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
