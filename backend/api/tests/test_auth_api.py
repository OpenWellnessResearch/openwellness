"""End-to-end HTTP tests for the email-OTP auth surface (the capstone matrix).

These drive the FULL stack through Starlette's ``TestClient``: real router,
real ``AuthService``, real ``JwtTokenService``, a real ``RedisOtpStore`` over
fakeredis, a real ``RefreshSessionStore`` over mongomock, and the registered
exception handlers. Nothing is mocked — the ONE sanctioned shortcut is reading
the delivered OTP code back out of the in-memory ``FakeEmailSender`` (the code
never leaves the email body otherwise).

Every test relies on the function-scoped ``app``/``client`` fixtures, so each
gets a fresh fakeredis + mongomock — no rate-limit/lockout bleed across tests.

The ``require_principal`` HTTP cases (enforce on/off) build their OWN small
FastAPI app so they don't pollute the main app's permissive auth container.
"""

from __future__ import annotations

import logging
from typing import Any

import pytest
from dependency_injector import providers
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from openwellness_api.auth.token_service import JwtTokenService
from openwellness_api.config import AuthSettings
from openwellness_api.deps.auth_container import AuthContainer, default_clock
from openwellness_api.deps.principal import Principal, require_principal
from openwellness_api.errors.handlers import register_exception_handlers
from openwellness_core.application.repositories import UserRepository
from openwellness_core.domain.models.user import User


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _auth_settings(app: FastAPI) -> AuthSettings:
    """The live ``AuthSettings`` the app's auth container is wired with."""
    return app.state.auth_container.auth_settings()


def _token_service(app: FastAPI) -> JwtTokenService:
    return app.state.auth_container.token_service()


def _login(
    client: TestClient,
    fake_email_sender: Any,
    email: str,
) -> dict[str, Any]:
    """Run a full send→verify login and return the parsed token body."""
    send = client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert send.status_code == 200, send.text
    code = fake_email_sender.last_code(email)
    assert code is not None, "no OTP code recorded for the login email"
    verify = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
    )
    assert verify.status_code == 200, verify.text
    return verify.json()


# --------------------------------------------------------------------------- #
# 1. Login happy path
# --------------------------------------------------------------------------- #
def test_login_happy_path(
    client: TestClient,
    app: FastAPI,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    email = seed_accounts["login_email"]

    send = client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert send.status_code == 200, send.text
    sbody = send.json()
    assert sbody["status"] == "OK"
    assert isinstance(sbody["message"], str) and sbody["message"]
    assert isinstance(sbody["expiresInSeconds"], int)
    assert isinstance(sbody["resendAfterSeconds"], int)

    code = fake_email_sender.last_code(email)
    assert isinstance(code, str)
    assert len(code) == 6 and code.isdigit()

    verify = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["accessToken"]
    assert body["tokenType"] == "Bearer"
    assert isinstance(body["expiresInSeconds"], int)
    assert body["refreshToken"]
    assert body["principal"]["userId"] == seed_accounts["login_user_id"]

    claims = _token_service(app).verify_access(body["accessToken"])
    assert claims.sub == seed_accounts["login_user_id"]
    assert claims.participant == seed_accounts["login_pid"]
    assert "participant" in claims.roles


# --------------------------------------------------------------------------- #
# 2. Registration happy path
# --------------------------------------------------------------------------- #
def test_registration_happy_path(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
    fakes: dict[type, Any],
) -> None:
    email = seed_accounts["reg_email"]
    pid = seed_accounts["reg_pid"]

    send = client.post(
        "/v1/auth:sendRegistrationCode",
        json={"email": email, "participant": f"participants/{pid}"},
    )
    assert send.status_code == 200, send.text
    sbody = send.json()
    assert sbody["status"] == "OK"
    assert sbody["message"]
    assert isinstance(sbody["expiresInSeconds"], int)
    assert isinstance(sbody["resendAfterSeconds"], int)

    code = fake_email_sender.last_code(email)
    assert isinstance(code, str) and len(code) == 6 and code.isdigit()

    verify = client.post(
        "/v1/auth:verifyRegistrationCode", json={"email": email, "code": code}
    )
    assert verify.status_code == 200, verify.text
    body = verify.json()
    assert body["accessToken"]
    assert body["tokenType"] == "Bearer"
    assert body["refreshToken"]
    assert body["principal"]["userId"] == seed_accounts["reg_user_id"]

    # bob is now a registered, active, verified account.
    bob = fakes[UserRepository].get_by_id(seed_accounts["reg_user_id"])
    assert bob is not None
    assert bob.verified_id  # truthy marker stamped
    assert bob.registered_at is not None
    assert bob.email == email
    assert bob.is_active is True


def test_register_then_login_composes(
    client: TestClient,
    app: FastAPI,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    """A freshly-registered user can immediately log in (the two flows compose:
    registration sets email + verified_id + is_active, which is exactly login's
    eligibility predicate)."""
    email = seed_accounts["reg_email"]
    pid = seed_accounts["reg_pid"]

    # 1) Register.
    send = client.post(
        "/v1/auth:sendRegistrationCode",
        json={"email": email, "participant": f"participants/{pid}"},
    )
    assert send.status_code == 200, send.text
    reg_code = fake_email_sender.last_code(email, "registration")
    assert reg_code is not None
    reg = client.post(
        "/v1/auth:verifyRegistrationCode", json={"email": email, "code": reg_code}
    )
    assert reg.status_code == 200, reg.text

    # 2) Now log in as the just-registered user (purpose-scoped rate-limit keys
    # mean the prior registration send doesn't trip the login cooldown).
    login_body = _login(client, fake_email_sender, email)
    assert login_body["accessToken"]
    assert login_body["refreshToken"]
    assert login_body["principal"]["userId"] == seed_accounts["reg_user_id"]
    claims = _token_service(app).verify_access(login_body["accessToken"])
    assert claims.sub == seed_accounts["reg_user_id"]


# --------------------------------------------------------------------------- #
# 3. Registration accepts a bare pid and the ``pid`` alias
# --------------------------------------------------------------------------- #
def test_registration_send_accepts_bare_pid(
    client: TestClient, seed_accounts: dict[str, Any]
) -> None:
    resp = client.post(
        "/v1/auth:sendRegistrationCode",
        json={"email": seed_accounts["reg_email"], "participant": seed_accounts["reg_pid"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "OK"


def test_registration_send_accepts_pid_alias(
    client: TestClient, seed_accounts: dict[str, Any]
) -> None:
    resp = client.post(
        "/v1/auth:sendRegistrationCode",
        json={"email": seed_accounts["reg_email"], "pid": seed_accounts["reg_pid"]},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "OK"


# --------------------------------------------------------------------------- #
# 4. Anti-enumeration — send (unknown subject) is indistinguishable + sends nothing
# --------------------------------------------------------------------------- #
def test_send_login_unknown_email_uniform_and_silent(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    known = client.post(
        "/v1/auth:sendLoginCode", json={"email": seed_accounts["login_email"]}
    )
    assert known.status_code == 200, known.text
    known_body = known.json()

    unknown_email = "nobody@example.com"
    unknown = client.post("/v1/auth:sendLoginCode", json={"email": unknown_email})
    assert unknown.status_code == 200, unknown.text
    unknown_body = unknown.json()

    # Byte-for-byte the same uniform send body (no enumeration leak).
    assert unknown_body == known_body

    # Nothing was actually delivered to the unknown address.
    assert fake_email_sender.last_code(unknown_email) is None
    assert all(e != unknown_email for (e, _c, _p) in fake_email_sender.sent)


def test_send_registration_unknown_participant_uniform_and_silent(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    eligible = client.post(
        "/v1/auth:sendRegistrationCode",
        json={"email": seed_accounts["reg_email"], "participant": seed_accounts["reg_pid"]},
    )
    assert eligible.status_code == 200, eligible.text
    eligible_body = eligible.json()

    unknown = client.post(
        "/v1/auth:sendRegistrationCode",
        json={"email": "ghost@example.com", "participant": "does-not-exist"},
    )
    assert unknown.status_code == 200, unknown.text
    assert unknown.json() == eligible_body
    assert fake_email_sender.last_code("ghost@example.com") is None
    assert all(e != "ghost@example.com" for (e, _c, _p) in fake_email_sender.sent)


# --------------------------------------------------------------------------- #
# 5. Anti-enumeration — verify failures are a single uniform 400
# --------------------------------------------------------------------------- #
def test_verify_failures_are_uniform_400(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    email = seed_accounts["login_email"]
    # Send so a record exists (the wrong-code path).
    assert (
        client.post("/v1/auth:sendLoginCode", json={"email": email}).status_code
        == 200
    )

    wrong_for_known = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": "000000"}
    )
    unknown_email = client.post(
        "/v1/auth:verifyLoginCode",
        json={"email": "nobody@example.com", "code": "123456"},
    )

    assert wrong_for_known.status_code == 400, wrong_for_known.text
    assert unknown_email.status_code == 400, unknown_email.text

    # Identical error bodies — no distinguishing signal between the two cases.
    assert wrong_for_known.json() == unknown_email.json()
    assert wrong_for_known.json()["error"]["status"] == "INVALID_ARGUMENT"


# --------------------------------------------------------------------------- #
# 6. Single-use: a correct code cannot be replayed
# --------------------------------------------------------------------------- #
def test_login_code_is_single_use(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    email = seed_accounts["login_email"]
    assert (
        client.post("/v1/auth:sendLoginCode", json={"email": email}).status_code
        == 200
    )
    code = fake_email_sender.last_code(email)
    assert code is not None

    first = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
    )
    assert first.status_code == 200, first.text

    replay = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
    )
    assert replay.status_code == 400, replay.text
    assert replay.json()["error"]["status"] == "INVALID_ARGUMENT"


# --------------------------------------------------------------------------- #
# 7. Verify lockout → 429 + Retry-After
# --------------------------------------------------------------------------- #
def test_verify_lockout_returns_429_with_retry_after(
    client: TestClient,
    app: FastAPI,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    email = seed_accounts["login_email"]
    max_attempts = _auth_settings(app).otp_max_attempts

    assert (
        client.post("/v1/auth:sendLoginCode", json={"email": email}).status_code
        == 200
    )
    real_code = fake_email_sender.last_code(email)
    assert real_code is not None

    # Burn wrong attempts until the lockout fires. The lockout triggers when the
    # incremented attempt count reaches max_attempts, i.e. the max_attempts-th
    # wrong attempt is the one that returns 429.
    locked: Any = None
    for i in range(max_attempts):
        resp = client.post(
            "/v1/auth:verifyLoginCode", json={"email": email, "code": "000000"}
        )
        if i < max_attempts - 1:
            assert resp.status_code == 400, (i, resp.text)
        else:
            locked = resp

    assert locked is not None
    assert locked.status_code == 429, locked.text
    assert "Retry-After" in locked.headers
    assert int(locked.headers["Retry-After"]) >= 1
    assert locked.json()["error"]["status"] == "RESOURCE_EXHAUSTED"

    # Even the correct code is now refused with 429 (the family is locked out).
    after = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": real_code}
    )
    assert after.status_code == 429, after.text
    assert "Retry-After" in after.headers


# --------------------------------------------------------------------------- #
# 8. Send rate-limit (resend cooldown) → 429 + Retry-After
# --------------------------------------------------------------------------- #
def test_send_resend_cooldown_returns_429(
    client: TestClient,
    seed_accounts: dict[str, Any],
) -> None:
    email = seed_accounts["login_email"]
    first = client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert first.status_code == 200, first.text

    second = client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert second.status_code == 429, second.text
    assert "Retry-After" in second.headers
    assert int(second.headers["Retry-After"]) >= 1
    assert second.json()["error"]["status"] == "RESOURCE_EXHAUSTED"


# --------------------------------------------------------------------------- #
# 9. Refresh rotation + reuse → 401 + whole-family revoke
# --------------------------------------------------------------------------- #
def test_refresh_rotation_and_reuse_revokes_family(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    body = _login(client, fake_email_sender, seed_accounts["login_email"])
    r1 = body["refreshToken"]

    rotate = client.post("/v1/auth:refreshToken", json={"refreshToken": r1})
    assert rotate.status_code == 200, rotate.text
    rbody = rotate.json()
    assert rbody["accessToken"]
    r2 = rbody["refreshToken"]
    assert r2 and r2 != r1

    # Replaying the OLD token is a reuse → 401.
    replay = client.post("/v1/auth:refreshToken", json={"refreshToken": r1})
    assert replay.status_code == 401, replay.text
    assert replay.json()["error"]["status"] == "UNAUTHENTICATED"

    # The reuse revoked the whole family, so the rotated token is dead too.
    after = client.post("/v1/auth:refreshToken", json={"refreshToken": r2})
    assert after.status_code == 401, after.text
    assert after.json()["error"]["status"] == "UNAUTHENTICATED"


# --------------------------------------------------------------------------- #
# 10. Revoke single → 401 thereafter; revoking unknown is idempotent
# --------------------------------------------------------------------------- #
def test_revoke_single_then_refresh_401(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    body = _login(client, fake_email_sender, seed_accounts["login_email"])
    r1 = body["refreshToken"]

    revoke = client.post("/v1/auth:revokeToken", json={"refreshToken": r1})
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["status"] == "OK"

    refresh = client.post("/v1/auth:refreshToken", json={"refreshToken": r1})
    assert refresh.status_code == 401, refresh.text
    assert refresh.json()["error"]["status"] == "UNAUTHENTICATED"


def test_revoke_unknown_token_is_idempotent(client: TestClient) -> None:
    resp = client.post(
        "/v1/auth:revokeToken", json={"refreshToken": "does-not-exist"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "OK"


# --------------------------------------------------------------------------- #
# 11. Revoke all (bearer-authenticated)
# --------------------------------------------------------------------------- #
def test_revoke_all_with_bearer_kills_sessions(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    body = _login(client, fake_email_sender, seed_accounts["login_email"])
    a1 = body["accessToken"]
    r1 = body["refreshToken"]

    revoke = client.post(
        "/v1/auth:revokeToken",
        json={"all": True},
        headers={"Authorization": f"Bearer {a1}"},
    )
    assert revoke.status_code == 200, revoke.text
    assert revoke.json()["status"] == "OK"

    refresh = client.post("/v1/auth:refreshToken", json={"refreshToken": r1})
    assert refresh.status_code == 401, refresh.text
    assert refresh.json()["error"]["status"] == "UNAUTHENTICATED"


def test_revoke_all_without_bearer_is_401(client: TestClient) -> None:
    resp = client.post("/v1/auth:revokeToken", json={"all": True})
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["status"] == "UNAUTHENTICATED"


# --------------------------------------------------------------------------- #
# 12. JWT claims on a login access token
# --------------------------------------------------------------------------- #
def test_login_access_token_claims(
    client: TestClient,
    app: FastAPI,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
) -> None:
    body = _login(client, fake_email_sender, seed_accounts["login_email"])
    # verify_access enforces iss/aud/exp/typ for us.
    claims = _token_service(app).verify_access(body["accessToken"])

    assert claims.iss == "openwellness-api"
    assert claims.aud == "openwellness-api"
    assert claims.sub == seed_accounts["login_user_id"]
    assert claims.participant == seed_accounts["login_pid"]
    assert isinstance(claims.roles, tuple)
    assert "participant" in claims.roles


# --------------------------------------------------------------------------- #
# 13. No OTP code / raw email in logs (security regression guard)
# --------------------------------------------------------------------------- #
def test_no_code_or_raw_email_in_logs(
    client: TestClient,
    seed_accounts: dict[str, Any],
    fake_email_sender: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    email = seed_accounts["login_email"]
    with caplog.at_level(logging.DEBUG):
        send = client.post("/v1/auth:sendLoginCode", json={"email": email})
        assert send.status_code == 200, send.text
        code = fake_email_sender.last_code(email)
        assert code is not None
        verify = client.post(
            "/v1/auth:verifyLoginCode", json={"email": email, "code": code}
        )
        assert verify.status_code == 200, verify.text

    assert code not in caplog.text
    assert email not in caplog.text


# --------------------------------------------------------------------------- #
# 14 & 15. require_principal at the HTTP layer (dedicated probe app)
# --------------------------------------------------------------------------- #
def _build_probe_app(*, enforce_principal: bool) -> tuple[FastAPI, JwtTokenService]:
    """A minimal app with one ``require_principal``-guarded probe route.

    Built standalone (NOT the conftest app) so the enforce-on/off toggle is
    isolated. The auth_settings and token_service share one settings instance,
    so signing and validation agree on secret/iss/aud.
    """
    settings = AuthSettings(
        jwt_secret="probe-secret-" * 4,
        jwt_issuer="openwellness-api",
        jwt_audience="openwellness-api",
        enforce_principal=enforce_principal,
    )
    token_service = JwtTokenService(settings=settings, clock=default_clock)

    container = AuthContainer()
    container.auth_settings.override(providers.Object(settings))
    container.token_service.override(providers.Object(token_service))

    app = FastAPI()
    register_exception_handlers(app)
    app.state.auth_container = container

    @app.get("/_probe")
    def probe(  # noqa: F811 - registered on the app router, not called directly
        principal: Principal = Depends(require_principal),
    ) -> dict[str, Any]:
        return {"id": principal.id, "authenticated": principal.is_authenticated}

    return app, token_service


def test_require_principal_http_enforce_on() -> None:
    app, token_service = _build_probe_app(enforce_principal=True)
    client = TestClient(app)

    # (a) No Authorization → 401 UNAUTHENTICATED.
    no_auth = client.get("/_probe")
    assert no_auth.status_code == 401, no_auth.text
    assert no_auth.json()["error"]["status"] == "UNAUTHENTICATED"

    # (b) Valid bearer → 200 authenticated.
    token = token_service.mint_access(
        user_id="U-probe", participant="P-probe", roles=["participant"]
    )
    ok = client.get("/_probe", headers={"Authorization": f"Bearer {token}"})
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body["authenticated"] is True
    assert body["id"] == "U-probe"


def test_require_principal_http_enforce_off_permissive() -> None:
    app, _token_service = _build_probe_app(enforce_principal=False)
    client = TestClient(app)

    resp = client.get("/_probe")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["authenticated"] is False
    assert body["id"] == "anonymous"


# --------------------------------------------------------------------------- #
# Staff (coach / admin) sign-in — D-01, D-03, D-05, ADR 0006
# --------------------------------------------------------------------------- #
def _add_staff(
    fakes: dict[type, Any], email: str, roles: dict[str, Any]
) -> str:
    """Store an active, never-registered (no verified_id) user with ``roles``."""
    user = User(
        id=f"staff-{email}",
        email=email,
        is_active=True,
        username=email.split("@")[0],
        verified_id=None,
        roles=roles,
    )
    fakes[UserRepository].store[user.id] = user
    return user.id


def test_staff_login_coach(
    client: TestClient,
    app: FastAPI,
    fakes: dict[type, Any],
    fake_email_sender: Any,
) -> None:
    email = "coach@example.com"
    uid = _add_staff(fakes, email, {"coach": {"studies": ["study-a"]}})

    body = _login(client, fake_email_sender, email)

    assert body["principal"]["userId"] == uid
    assert body["principal"]["participant"] is None
    claims = _token_service(app).verify_access(body["accessToken"])
    assert claims.participant is None
    assert claims.roles == ("coach",)
    assert claims.coach_studies == ("study-a",)


def test_staff_login_admin(
    client: TestClient,
    app: FastAPI,
    fakes: dict[type, Any],
    fake_email_sender: Any,
) -> None:
    email = "admin@example.com"
    _add_staff(fakes, email, {"admin": {}})

    body = _login(client, fake_email_sender, email)

    claims = _token_service(app).verify_access(body["accessToken"])
    assert claims.roles == ("admin",)
    assert claims.coach_studies == ()


def test_staff_login_no_role_stays_locked_out(
    client: TestClient,
    fakes: dict[type, Any],
    fake_email_sender: Any,
) -> None:
    email = "norole@example.com"
    _add_staff(fakes, email, {})

    send = client.post("/v1/auth:sendLoginCode", json={"email": email})
    assert send.status_code == 200, send.text
    assert fake_email_sender.last_code(email) is None

    verify = client.post(
        "/v1/auth:verifyLoginCode", json={"email": email, "code": "000000"}
    )
    assert verify.status_code == 400, verify.text


def test_staff_login_uniform_send_body(
    client: TestClient,
    fakes: dict[type, Any],
) -> None:
    _add_staff(fakes, "coach2@example.com", {"coach": {"studies": []}})

    staff = client.post(
        "/v1/auth:sendLoginCode", json={"email": "coach2@example.com"}
    )
    unknown = client.post(
        "/v1/auth:sendLoginCode", json={"email": "nobody@example.com"}
    )

    assert staff.status_code == unknown.status_code == 200
    assert staff.json() == unknown.json()
