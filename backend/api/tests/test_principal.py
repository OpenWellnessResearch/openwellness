"""Unit tests for the strict ``get_principal``.

A lightweight fake ``Request`` supplies ``.headers`` and
``.app.state.auth_container``. Valid-bearer cases mint a REAL access JWT via a
real :class:`JwtTokenService` (PyJWT is never mocked).

The contract: a verified bearer yields a ``Principal``; anything else raises the
401 UNAUTHENTICATED envelope. ``X-Principal-Id`` is never read.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers

from openwellness_api.auth.token_service import JwtTokenService
from openwellness_api.config import AuthSettings
from openwellness_api.deps.principal import Principal, get_principal


class _FakeRequest:
    """Minimal Request: case-insensitive ``.headers`` and ``.app.state``."""

    def __init__(
        self, headers: dict[str, str] | None = None, *, auth_container: Any = None
    ) -> None:
        self.headers = Headers(headers or {})
        state = type("State", (), {})()
        if auth_container is not None:
            state.auth_container = auth_container
        self.app = type("App", (), {"state": state})()


def _settings() -> AuthSettings:
    return AuthSettings(
        jwt_secret="x" * 40,
        jwt_issuer="openwellness-api",
        jwt_audience="openwellness-api",
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


class _FakeAuthContainer:
    def __init__(self, token_service: JwtTokenService) -> None:
        self._token_service = token_service

    def token_service(self) -> JwtTokenService:
        return self._token_service


def _svc() -> JwtTokenService:
    return JwtTokenService(settings=_settings(), clock=_now)


def _get(headers: dict[str, str], svc: JwtTokenService | None = None) -> Principal:
    req = _FakeRequest(headers, auth_container=_FakeAuthContainer(svc or _svc()))
    return get_principal(req)  # type: ignore[arg-type]


def _assert_401(headers: dict[str, str], svc: JwtTokenService | None = None) -> None:
    with pytest.raises(HTTPException) as excinfo:
        _get(headers, svc)
    exc = excinfo.value
    assert exc.status_code == 401
    detail = cast("dict[str, Any]", exc.detail)
    assert detail["error"]["status"] == "UNAUTHENTICATED"
    assert detail["error"]["code"] == 401


def test_valid_bearer_returns_principal() -> None:
    token = _svc().mint_access(
        user_id="U1",
        participant="P1",
        roles=["coach"],
        coach_studies=["S1", "S2"],
    )

    p = _get({"Authorization": f"Bearer {token}"})

    assert p == Principal(
        id="U1", roles=("coach",), participant="P1", coach_studies=("S1", "S2")
    )


def test_bearer_scheme_is_case_insensitive() -> None:
    token = _svc().mint_access(user_id="U1")
    assert _get({"Authorization": f"bEaReR {token}"}).id == "U1"


def test_forged_x_principal_id_beside_valid_bearer_changes_nothing() -> None:
    token = _svc().mint_access(user_id="U1")

    p = _get({"Authorization": f"Bearer {token}", "X-Principal-Id": "forged"})

    assert p.id == "U1"


def test_x_principal_id_alone_is_401() -> None:
    _assert_401({"X-Principal-Id": "caller-1"})


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer "},
        {"Authorization": "Bearer    "},
        {"Authorization": "Basic abc"},
        {"Authorization": "Bearer not.a.jwt"},
    ],
    ids=["missing", "blank", "blank-spaces", "non-bearer", "garbage"],
)
def test_bad_header_is_401(headers: dict[str, str]) -> None:
    _assert_401(headers)


def test_expired_token_is_401() -> None:
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    token = JwtTokenService(settings=_settings(), clock=lambda: past).mint_access(
        user_id="U1"
    )
    _assert_401({"Authorization": f"Bearer {token}"})


def test_no_auth_container_is_an_error_not_an_anonymous_pass() -> None:
    token = _svc().mint_access(user_id="U1")
    req = _FakeRequest({"Authorization": f"Bearer {token}"})

    with pytest.raises(AttributeError):
        get_principal(req)  # type: ignore[arg-type]


def test_is_admin() -> None:
    assert Principal(id="u", roles=("admin",)).is_admin
    assert not Principal(id="u", roles=("coach",)).is_admin
