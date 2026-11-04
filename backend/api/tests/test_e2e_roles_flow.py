"""The floor (AUTH-01): a signed-in caller reaches a resource route, anyone else is 401.

The 401 must come before FastAPI parses the body, so an anonymous caller gets
the same answer whatever the body holds. ``/v1/auth:*`` stays outside the floor.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openwellness_api.auth.token_service import JwtTokenService

from .conftest import TEST_ADMIN_ID, token_for

URL = "/v1/users/any/weights"
JSON_CT = {"Content-Type": "application/json"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _sign_in(
    anon_client: TestClient, fake_email_sender: Any, email: str
) -> str:
    send = anon_client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert send.status_code == 200, send.text
    code = fake_email_sender.last_code(email)
    verify = anon_client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
    )
    assert verify.status_code == 200, verify.text
    return verify.json()["accessToken"]


def _expired_token(app: FastAPI) -> str:
    settings = app.state.auth_container.auth_settings()
    past = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return JwtTokenService(settings=settings, clock=lambda: past).mint_access(
        user_id="u"
    )


def _unauthenticated(resp: Any) -> dict[str, Any]:
    assert resp.status_code == 401, resp.text
    body = resp.json()
    assert body["error"]["status"] == "UNAUTHENTICATED"
    return body


def test_signed_in_caller_reaches_a_resource_route(
    anon_client: TestClient, seed_accounts: dict[str, Any], fake_email_sender: Any
) -> None:
    token = _sign_in(anon_client, fake_email_sender, seed_accounts["login_email"])
    resp = anon_client.get(URL, headers=_bearer(token))
    assert resp.status_code == 200, resp.text


def test_anonymous_is_401(anon_client: TestClient) -> None:
    _unauthenticated(anon_client.get(URL))


def test_blank_and_bad_bearer_are_401(app: FastAPI, anon_client: TestClient) -> None:
    expected = _unauthenticated(anon_client.get(URL))
    for header in (
        "Bearer ",
        "Basic x",
        "Bearer not.a.jwt",
        f"Bearer {_expired_token(app)}",
    ):
        resp = anon_client.get(URL, headers={"Authorization": header})
        assert _unauthenticated(resp) == expected, header
        assert "www-authenticate" not in resp.headers


@pytest.mark.parametrize("body", [b"{", b'{"a":"\xff"}'])
def test_anonymous_unparseable_body_is_401(
    anon_client: TestClient, body: bytes
) -> None:
    expected = _unauthenticated(anon_client.get(URL))
    resp = anon_client.post(URL, content=body, headers=JSON_CT)
    assert resp.status_code == 401, resp.text
    assert resp.json() == expected


def test_bad_bearer_with_unparseable_body_is_401(anon_client: TestClient) -> None:
    resp = anon_client.post(
        URL, content=b"{", headers={**JSON_CT, **_bearer("not.a.jwt")}
    )
    _unauthenticated(resp)


def test_authenticated_unparseable_body_keeps_the_400(app: FastAPI) -> None:
    token = token_for(app, user_id=TEST_ADMIN_ID, roles=["admin"])
    c = TestClient(app, headers=_bearer(token))
    bad = c.post(URL, content=b"{", headers=JSON_CT)
    assert bad.status_code == 400, bad.text
    assert bad.json()["error"]["status"] == "INVALID_ARGUMENT"
    invalid_utf8 = c.post(URL, content=b'{"a":"\xff"}', headers=JSON_CT)
    assert invalid_utf8.status_code == 400, invalid_utf8.text


def test_auth_routes_stay_outside_the_floor(anon_client: TestClient) -> None:
    ok = anon_client.post("/v1/auth:sendLoginCode", json={"email": "x@example.com"})
    assert ok.status_code == 200, ok.text
    assert isinstance(ok.json(), dict)
    bad = anon_client.post(
        "/v1/auth:sendLoginCode", content=b"{", headers=JSON_CT
    )
    assert bad.status_code == 400, bad.text
