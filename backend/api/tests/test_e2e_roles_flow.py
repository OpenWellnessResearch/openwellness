"""The floor (AUTH-01): a signed-in caller reaches a resource route, anyone else is 401.

The 401 must come before FastAPI parses the body, so an anonymous caller gets
the same answer whatever the body holds. ``/v1/auth:*`` stays outside the floor.
"""

from __future__ import annotations

import runpy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openwellness_api.auth.token_service import JwtTokenService
from openwellness_core.domain.models.weight import Weight

from .conftest import TEST_ADMIN_ID, World, token_for

URL = "/v1/users/any/weights"
JSON_CT = {"Content-Type": "application/json"}


def _bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(
    anon_client: TestClient, fake_email_sender: Any, email: str
) -> dict[str, Any]:
    send = anon_client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert send.status_code == 200, send.text
    code = fake_email_sender.last_code(email)
    verify = anon_client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
    )
    assert verify.status_code == 200, verify.text
    return verify.json()


def _sign_in(
    anon_client: TestClient, fake_email_sender: Any, email: str
) -> str:
    return _login(anon_client, fake_email_sender, email)["accessToken"]


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
    # Under their own participant id: another id is 404 once the policy runs.
    resp = anon_client.get(
        f"/v1/users/{seed_accounts['login_pid']}/weights", headers=_bearer(token)
    )
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


def _seed_weight(app: FastAPI, world: World) -> None:
    """Stored directly: create is not the path under test here."""
    app.state.container.repositories.weight().store["w-a"] = Weight(
        id="w-a", owner=world.p_a, study_id=world.study_a, weight=1.0
    )


def test_coach_lists_in_study_weights(
    app: FastAPI, anon_client: TestClient, world: World, fake_email_sender: Any
) -> None:
    _seed_weight(app, world)
    token = _sign_in(anon_client, fake_email_sender, "coach-in@example.com")
    resp = anon_client.get(f"/v1/users/{world.p_a}/weights", headers=_bearer(token))
    assert resp.status_code == 200, resp.text
    assert [w["name"] for w in resp.json()["weights"]] == ["users/p-a/weights/w-a"]


def test_coach_other_study_is_404(
    app: FastAPI, anon_client: TestClient, world: World, fake_email_sender: Any
) -> None:
    _seed_weight(app, world)
    token = _sign_in(anon_client, fake_email_sender, "coach-other@example.com")
    resp = anon_client.get(f"/v1/users/{world.p_a}/weights", headers=_bearer(token))
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["status"] == "NOT_FOUND"


# --------------------------------------------------------------------------- #
# Per-role session over HTTP on the fakes, from the same seed the manual UAT
# runs (D-04, D-11, D-12). Tokens come from the real OTP endpoints.
# --------------------------------------------------------------------------- #

SEED_PATH = Path(__file__).resolve().parents[1] / "scripts" / "dev_seed.py"
DOCKERIGNORE = Path(__file__).resolve().parents[2] / ".dockerignore"


def _seed_args(app: FastAPI) -> dict[str, Any]:
    repos = app.state.container.repositories
    return {
        "users": repos.user(),
        "studies": repos.study(),
        "participants": repos.participant(),
    }


@pytest.fixture
def seed_dev(app: FastAPI) -> Any:
    """Callable that runs the dev seed (loaded by path: it is not a package)."""
    run = runpy.run_path(str(SEED_PATH))["seed_dev_data"]
    return lambda: run(**_seed_args(app))


def _post(client: TestClient, path: str, body: dict[str, Any], token: str | None = None) -> Any:
    headers = _bearer(token) if token else {}
    return client.post(path, json=body, headers=headers)


def _session(
    anon_client: TestClient,
    sender: Any,
    email: str,
    call: Any,
) -> None:
    """Sign in, restore (refresh), call again, sign out, and prove the sign-out."""
    first = _login(anon_client, sender, email)
    call(first["accessToken"], first["principal"])
    # The dashboard restores a session by refreshing (AuthContext bootstrap).
    refreshed = _post(
        anon_client, "/v1/auth:refreshToken", {"refreshToken": first["refreshToken"]}
    )
    assert refreshed.status_code == 200, refreshed.text
    again = refreshed.json()
    call(again["accessToken"], first["principal"])
    revoke = _post(
        anon_client, "/v1/auth:revokeToken", {"refreshToken": again["refreshToken"]}
    )
    assert revoke.status_code == 200, revoke.text
    dead = _post(
        anon_client, "/v1/auth:refreshToken", {"refreshToken": again["refreshToken"]}
    )
    assert dead.status_code == 401, dead.text


def test_seed_creates_one_of_each(app: FastAPI, seed_dev: Any) -> None:
    seeded = seed_dev()
    args = _seed_args(app)
    assert len(args["studies"].store) == 1
    assert len(args["users"].store) == 3
    admin = args["users"].get_by_email(seeded.admin_email)[0]
    coach = args["users"].get_by_email(seeded.coach_email)[0]
    person = args["users"].get_by_email(seeded.participant_email)[0]
    assert "admin" in admin.roles
    assert coach.roles["coach"]["studies"] == [seeded.study_id]
    participant = args["participants"].get_by_id(seeded.participant_id)
    assert participant.study_id == seeded.study_id
    assert participant.user_id == person.id
    assert person.roles["participant"]["pid"] == seeded.participant_id
    assert person.verified_id


def test_seed_is_idempotent(app: FastAPI, seed_dev: Any) -> None:
    first = seed_dev()
    args = _seed_args(app)
    counts = {k: len(v.store) for k, v in args.items()}
    assert seed_dev() == first
    assert {k: len(v.store) for k, v in args.items()} == counts


def test_admin_flow(
    app: FastAPI, anon_client: TestClient, fake_email_sender: Any, seed_dev: Any
) -> None:
    seeded = seed_dev()

    def call(token: str, _principal: dict[str, Any]) -> None:
        resp = anon_client.get("/v1/users", headers=_bearer(token))
        assert resp.status_code == 200, resp.text

    _session(anon_client, fake_email_sender, seeded.admin_email, call)


def test_coach_flow(
    app: FastAPI, anon_client: TestClient, fake_email_sender: Any, seed_dev: Any
) -> None:
    seeded = seed_dev()

    def call(token: str, _principal: dict[str, Any]) -> None:
        listed = anon_client.get(
            f"/v1/studies/{seeded.study_id}/participants", headers=_bearer(token)
        )
        assert listed.status_code == 200, listed.text
        assert [p["name"] for p in listed.json()["participants"]] == [
            f"studies/{seeded.study_id}/participants/{seeded.participant_id}"
        ]
        weights = anon_client.get(
            f"/v1/users/{seeded.participant_id}/weights", headers=_bearer(token)
        )
        assert weights.status_code == 200, weights.text

    _session(anon_client, fake_email_sender, seeded.coach_email, call)


def test_participant_flow(
    app: FastAPI, anon_client: TestClient, fake_email_sender: Any, seed_dev: Any
) -> None:
    seeded = seed_dev()
    url = f"/v1/users/{seeded.participant_id}/weights"
    calls = 0

    def call(token: str, principal: dict[str, Any]) -> None:
        nonlocal calls
        calls += 1
        made = _post(anon_client, url, {"weight": 70.0 + calls}, token)
        assert made.status_code == 201, made.text
        assert made.json()["updatedBy"] == principal["userId"]
        listed = anon_client.get(url, headers=_bearer(token))
        assert listed.status_code == 200, listed.text
        assert len(listed.json()["weights"]) == calls

    _session(anon_client, fake_email_sender, seeded.participant_email, call)


def test_revoke_all_needs_the_bearer(
    anon_client: TestClient, fake_email_sender: Any, seed_dev: Any
) -> None:
    seeded = seed_dev()
    tokens = _login(anon_client, fake_email_sender, seeded.coach_email)
    assert _post(anon_client, "/v1/auth:revokeToken", {"all": True}).status_code == 401
    revoked = _post(
        anon_client, "/v1/auth:revokeToken", {"all": True}, tokens["accessToken"]
    )
    assert revoked.status_code == 200, revoked.text
    dead = _post(
        anon_client, "/v1/auth:refreshToken", {"refreshToken": tokens["refreshToken"]}
    )
    assert dead.status_code == 401, dead.text


def test_participant_cannot_reach_coach_surface_after_seed(
    anon_client: TestClient, fake_email_sender: Any, seed_dev: Any
) -> None:
    seeded = seed_dev()
    token = _sign_in(anon_client, fake_email_sender, seeded.participant_email)
    resp = anon_client.get(
        f"/v1/studies/{seeded.study_id}/participants", headers=_bearer(token)
    )
    assert resp.status_code == 403, resp.text


def test_seed_script_is_excluded_from_image() -> None:
    assert "api/scripts" in DOCKERIGNORE.read_text().splitlines()
