"""AUTH-01, AUTH-02, D-14: every route on the real app refuses an anonymous caller,
and every resource route carries exactly one policy decision.

The app comes from ``build_test_app``, which calls ``create_app``, so the walk
sees the same route table a deployment serves. Failures are collected into one
sorted list and compared to ``[]`` so a failure names every offending route.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from openwellness_api import auth
from openwellness_api.auth.email_sender import FakeEmailSender
from openwellness_api.authz.engine import authorize
from openwellness_api.authz.policy import CUSTOM_OPS, OPS, POLICY
from openwellness_api.config import AuthSettings
from openwellness_api.resources import RESOURCE_MODULES
from openwellness_api.v1 import FloorRoute

from .conftest import TEST_ADMIN_ID, make_fakes, token_for

MIN_PAIRS = 254
BAD_JSON = {"content": "{", "headers": {"Content-Type": "application/json"}}


@pytest.fixture(scope="module")
def real_app(app_builder: Any) -> FastAPI:
    instance = app_builder(make_fakes(), FakeEmailSender())
    yield instance
    instance.state.container.unwire()


def _url(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "x", path)


def _floored(app: FastAPI) -> list[tuple[str, str]]:
    """Every (method, url) the floor must answer, one pair per method and path."""
    return sorted(
        (method, _url(route.path))
        for route in app.routes
        if isinstance(route, FloorRoute)
        for method in route.methods
    )


def _walk(app: FastAPI, headers: dict[str, str], **kwargs: Any) -> list[str]:
    client = TestClient(app, headers=headers, raise_server_exceptions=False)
    pairs = _floored(app)
    assert len(pairs) >= MIN_PAIRS, f"only {len(pairs)} pairs: the route table is partial"
    return sorted(
        f"{method} {url} -> {resp.status_code}"
        for method, url in pairs
        if (resp := client.request(method, url, **kwargs)).status_code != 401
    )


def test_anonymous_gets_401_on_every_route(real_app: FastAPI) -> None:
    assert _walk(real_app, {}) == []


def test_anonymous_unparseable_body_gets_401_on_every_route(real_app: FastAPI) -> None:
    assert _walk(real_app, BAD_JSON["headers"], content="{") == []


def _bad_bearers(app: FastAPI) -> dict[str, str]:
    s = AuthSettings()
    now = datetime.now(timezone.utc)

    def forge(secret: str | None = None, **over: Any) -> str:
        claims: dict[str, Any] = {
            "iss": s.jwt_issuer,
            "sub": "u1",
            "aud": s.jwt_audience,
            "iat": now,
            "exp": now + timedelta(seconds=900),
            "typ": "access",
            "roles": ["admin"],
        }
        claims.update(over)
        return jwt.encode(claims, secret or s.jwt_secret, algorithm=s.jwt_alg)

    return {
        "garbage": "Bearer not-a-token",
        "expired": "Bearer "
        + forge(iat=now - timedelta(hours=2), exp=now - timedelta(hours=1)),
        "wrong-audience": "Bearer " + forge(aud="someone-else"),
        "wrong-secret": "Bearer " + forge(secret="x" * 40),
        "typ-not-access": "Bearer " + forge(typ="refresh"),
        "blank-token": "Bearer ",
    }


@pytest.mark.parametrize(
    "kind", ["garbage", "expired", "wrong-audience", "wrong-secret", "typ-not-access", "blank-token"]
)
def test_bad_bearer_gets_401_on_every_route(real_app: FastAPI, kind: str) -> None:
    header = _bad_bearers(real_app)[kind]
    assert _walk(real_app, {"Authorization": header}) == []


def test_exempt_routes_are_exact(real_app: FastAPI) -> None:
    exempt = {
        (method, route.path)
        for route in real_app.routes
        if not isinstance(route, FloorRoute)
        for method in route.methods  # type: ignore[attr-defined]
    }
    expected = {("GET", "/healthz")} | {
        (method, "/v1" + r.path)
        for r in auth.build_router().routes
        if isinstance(r, APIRoute)
        for method in r.methods
    }
    assert exempt == expected


def test_only_api_routes_are_registered(real_app: FastAPI) -> None:
    assert [r.path for r in real_app.routes if not isinstance(r, APIRoute)] == []


def _implied_op(module: str, method: str, path: str) -> str:
    last = path.rsplit("/", 1)[-1]
    if ":" in last:
        verb = last.rsplit(":", 1)[1]
        return CUSTOM_OPS.get(module, {}).get(verb, verb)
    if method == "POST":
        return "create"
    if method == "GET":
        return "get" if last.startswith("{") else "list"
    return {"PATCH": "patch", "DELETE": "delete"}[method]


def test_every_resource_route_has_one_authorize() -> None:
    bad: list[str] = []
    for mod in RESOURCE_MODULES:
        name = mod.__name__.rsplit(".", 1)[-1]
        for route in mod.build_router().routes:
            assert isinstance(route, APIRoute)
            calls = [
                d.call
                for d in route.dependant.dependencies
                if isinstance(d.call, authorize)
            ]
            for method in route.methods:
                label = f"{name} {method} {route.path}"
                if len(calls) != 1:
                    bad.append(f"{label}: {len(calls)} authorize")
                    continue
                call = calls[0]
                want = _implied_op(name, method, route.path)
                if call.module != name or call.op != want or call.op not in OPS:
                    bad.append(f"{label}: has ({call.module}, {call.op}), want ({name}, {want})")
    assert sorted(bad) == []


def test_all_36_modules_are_rolled_out() -> None:
    covered = {
        mod.__name__.rsplit(".", 1)[-1]
        for mod in RESOURCE_MODULES
        if any(
            isinstance(d.call, authorize)
            for route in mod.build_router().routes
            for d in route.dependant.dependencies  # type: ignore[attr-defined]
        )
    }
    assert covered == set(POLICY)
    assert len(covered) == 36


def test_healthz_is_anonymous(real_app: FastAPI) -> None:
    assert TestClient(real_app).get("/healthz").status_code == 200


def test_typed_invalid_body_is_401(real_app: FastAPI) -> None:
    resp = TestClient(real_app).post("/v1/users/x/weights", json={"weight": "nan-text"})
    assert resp.status_code == 401


def test_authenticated_unparseable_json_keeps_the_400(real_app: FastAPI) -> None:
    token = token_for(real_app, user_id=TEST_ADMIN_ID, roles=["admin"])
    resp = TestClient(real_app, headers={"Authorization": f"Bearer {token}"}).post(
        "/v1/users/x/weights", **BAD_JSON
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["status"] == "INVALID_ARGUMENT"


def test_exempt_route_unparseable_json_keeps_the_400(real_app: FastAPI) -> None:
    resp = TestClient(real_app).post("/v1/auth:sendLoginCode", **BAD_JSON)
    assert resp.status_code == 400, resp.text
    assert resp.json()["error"]["status"] == "INVALID_ARGUMENT"
