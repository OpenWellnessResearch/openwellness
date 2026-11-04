"""Admin-only rows under the policy engine: ``user``, ``admin`` and ``app`` (AUTH-04).

Closes the duplicate-email oracle: ``POST /v1/users`` is an admin-only cell, and
``authorize`` runs before the handler, so a non-admin never reaches the 409.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from openwellness_core.application.exceptions import DuplicateEntityException

from .conftest import World, token_for

USER_BODY = {"email": "a@example.com", "isActive": True, "username": "dup"}


def _client(app: FastAPI, **token: Any) -> TestClient:
    bearer = token_for(app, user_id="u-edge", **token)
    return TestClient(app, headers={"Authorization": f"Bearer {bearer}"})


# -- user ----------------------------------------------------------------------


@pytest.mark.parametrize("caller", ["owner_self", "coach_in", "no_role"])
def test_non_admin_403_on_user_list(app: FastAPI, world: World, caller: str) -> None:
    assert world.client(app, caller).get("/v1/users").status_code == 403


def test_duplicate_email_is_403_for_non_admin(app: FastAPI, world: World) -> None:
    repo = app.state.container.repositories.user()
    existing = {u.email for u in repo.store.values()}

    def create(entity: Any) -> Any:
        if entity.email in existing:
            raise DuplicateEntityException("email already registered")
        return type(repo).create(repo, entity)

    repo.create = create  # the instance wins over the class attribute
    body = {**USER_BODY, "email": "u-a@example.com"}
    assert world.client(app, "admin").post("/v1/users", json=body).status_code == 409
    for caller in ("coach_in", "owner_self", "no_role"):
        resp = world.client(app, caller).post("/v1/users", json=body)
        assert resp.status_code == 403, (caller, resp.text)


def test_self_user_binds_to_sub(app: FastAPI, world: World) -> None:
    own = world.client(app, "owner_self")
    assert own.get("/v1/users/u-a").status_code == 200
    assert own.get("/v1/users/u-b").status_code == 404
    assert own.patch("/v1/users/u-a", json={"location": "NY"}).status_code == 403
    assert world.client(app, "coach_in").get("/v1/users/u-ci").status_code == 200


def test_admin_patch_can_edit_roles(app: FastAPI, world: World) -> None:
    url = "/v1/users/u-a"
    new_roles = {"participant": {"pid": "p-a"}, "coach": {"studies": ["study-a"]}}
    resp = world.client(app, "admin").patch(url, json={"roles": new_roles})
    assert resp.status_code == 200, resp.text
    assert resp.json()["roles"] == new_roles
    stored = app.state.container.repositories.user().store["u-a"]
    assert stored.roles == new_roles
    resp = world.client(app, "owner_self").patch(url, json={"roles": {}})
    assert resp.status_code == 403
    assert stored.roles == new_roles


# -- admin and app -------------------------------------------------------------


@pytest.mark.parametrize("path", ["/v1/admins", "/v1/apps"])
@pytest.mark.parametrize("caller", ["owner_self", "coach_in", "no_role"])
def test_non_admin_403_on_admin_resources(
    app: FastAPI, world: World, caller: str, path: str
) -> None:
    assert world.client(app, caller).get(path).status_code == 403


@pytest.mark.parametrize("roles", [["administrator"], ["Admin"]])
def test_role_match_is_exact(app: FastAPI, roles: list[str]) -> None:
    assert _client(app, roles=roles).get("/v1/admins").status_code == 403


def test_empty_roles_is_403(app: FastAPI) -> None:
    client = _client(app, roles=[])
    assert client.get("/v1/admins").status_code == 403
    assert client.get("/v1/users").status_code == 403


@pytest.mark.parametrize("roles", [["participant", "admin"], ["admin", "participant"]])
def test_role_order_is_irrelevant(app: FastAPI, roles: list[str]) -> None:
    assert _client(app, roles=roles).get("/v1/admins").status_code == 200


def test_admin_round_trip(app: FastAPI, world: World) -> None:
    admin = world.client(app, "admin")
    body = {"name": {"first": "Ada"}, "user": {"id": "u-a", "name": "Ada"}}
    resp = admin.post("/v1/admins", json=body)
    assert resp.status_code == 201, resp.text
    assert resp.json()["user"]["id"] == "u-a"
    got = admin.get("/v1/" + resp.json()["name"])
    assert got.status_code == 200, got.text
    assert got.json()["user"]["name"] == "Ada"
