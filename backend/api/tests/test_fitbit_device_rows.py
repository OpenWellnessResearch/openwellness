"""Device and Fitbit rows under the policy engine (AUTH-03, AUTH-05, ADR 0007).

A participant reads only their own devices and Fitbit connection; the OAuth
tokens of a Fitbit never reach a non-admin, the participant included. Rows are
stored through an admin client so the tests do not depend on the repository.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from .conftest import World

F = "/v1/fitbits"
D = "/v1/devices"
TOKENS = {"accessToken": "acc-secret", "refreshToken": "ref-secret"}


def _put(admin: TestClient, url: str, body: dict[str, Any]) -> str:
    resp = admin.post(url, json=body)
    assert resp.status_code == 201, resp.text
    return resp.json()["name"].rsplit("/", 1)[1]


def _fitbit(admin: TestClient, pid: str = "p-a") -> str:
    return _put(admin, F, {"participantId": pid, **TOKENS})


def _device(admin: TestClient, pid: str) -> str:
    return _put(admin, D, {"serialNumber": f"sn-{pid}", "participantId": pid})


def test_fitbit_tokens_null_for_owner(app: FastAPI, world: World) -> None:
    fid = _fitbit(world.client(app, "admin"))
    resp = world.client(app, "owner_self").get(f"{F}/{fid}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["participantId"] == "p-a"
    assert body["accessToken"] is None
    assert body["refreshToken"] is None
    assert "secret" not in resp.text


def test_fitbit_tokens_visible_to_admin(app: FastAPI, world: World) -> None:
    admin = world.client(app, "admin")
    created = admin.post(F, json={"participantId": "p-a", **TOKENS})
    assert created.status_code == 201, created.text
    fid = created.json()["name"].rsplit("/", 1)[1]
    patched = admin.patch(f"{F}/{fid}", json={"ownerId": "o"})
    undeleted = admin.post(f"{F}/{fid}:undelete")
    responses = {
        "get": admin.get(f"{F}/{fid}").json(),
        "list": admin.get(F).json()["fitbits"][0],
        "create": created.json(),
        "patch": patched.json(),
        "undelete": undeleted.json(),
    }
    for path, body in responses.items():
        assert (body["accessToken"], body["refreshToken"]) == ("acc-secret", "ref-secret"), path


def test_fitbit_other_participant_is_404(app: FastAPI, world: World) -> None:
    fid = _fitbit(world.client(app, "admin"))
    assert world.client(app, "owner_other").get(f"{F}/{fid}").status_code == 404


def test_fitbit_non_admin_paths(app: FastAPI, world: World) -> None:
    fid = _fitbit(world.client(app, "admin"))
    me = world.client(app, "owner_self")
    assert me.patch(f"{F}/{fid}", json={"ownerId": "o"}).status_code == 403
    assert me.post(F, json={"participantId": "p-a"}).status_code == 403
    assert me.get(F).status_code == 403
    assert world.client(app, "coach_in").get(f"{F}/{fid}").status_code == 403


def test_device_list_is_own_only(app: FastAPI, world: World) -> None:
    admin = world.client(app, "admin")
    _device(admin, "p-a")
    _device(admin, "p-b")

    def serials(caller: str) -> list[str]:
        resp = world.client(app, caller).get(D)
        assert resp.status_code == 200, resp.text
        return [d["serialNumber"] for d in resp.json()["devices"]]

    assert serials("owner_self") == ["sn-p-a"]
    assert serials("owner_other") == ["sn-p-b"]


def test_device_get_scope(app: FastAPI, world: World) -> None:
    admin = world.client(app, "admin")
    mine, theirs = _device(admin, "p-a"), _device(admin, "p-b")
    me = world.client(app, "owner_self")
    assert me.get(f"{D}/{mine}").status_code == 200
    assert me.get(f"{D}/{theirs}").status_code == 404
    assert world.client(app, "coach_in").get(f"{D}/{mine}").status_code == 403
    assert me.patch(f"{D}/{mine}", json={"platform": "ios"}).status_code == 403
