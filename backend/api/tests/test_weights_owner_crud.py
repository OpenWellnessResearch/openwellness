"""Owner-scoped CRUD + owner-mismatch behavior for Weights (AIP wire format)."""

from .conftest import TEST_ADMIN_ID


def test_weight_owner_scoped_crud(client) -> None:
    # Create under user-1
    r = client.post("/v1/users/user-1/weights", json={"weight": 180.5})
    assert r.status_code == 201, r.text
    created = r.json()
    name = created["name"]
    assert name.startswith("users/user-1/weights/")
    weight_id = name.rsplit("/", 1)[1]
    assert created["owner"] == "user-1"
    assert created["updatedBy"] == TEST_ADMIN_ID
    assert created["createTime"].endswith("Z")

    # Get under user-1
    r = client.get(f"/v1/users/user-1/weights/{weight_id}")
    assert r.status_code == 200

    # Get under user-2 (owner mismatch) — should 404, not 403
    r = client.get(f"/v1/users/user-2/weights/{weight_id}")
    assert r.status_code == 404

    # Patch
    r = client.patch(
        f"/v1/users/user-1/weights/{weight_id}", json={"weight": 179.0}
    )
    assert r.status_code == 200
    assert r.json()["weight"] == 179.0

    # List with startTime/endTime
    r = client.get(
        "/v1/users/user-1/weights",
        params={"startTime": "2020-01-01", "endTime": "2030-01-01"},
    )
    assert r.status_code == 200
    body = r.json()
    assert len(body["weights"]) == 1
    assert body["weights"][0]["name"] == name

    # Archive
    r = client.delete(f"/v1/users/user-1/weights/{weight_id}")
    assert r.status_code == 204

    # Undelete restores the archived copy.
    r = client.post(f"/v1/users/user-1/weights/{weight_id}:undelete")
    assert r.status_code == 200
    assert r.json()["name"] == name

    # Purge (hard delete)
    r = client.post(f"/v1/users/user-1/weights/{weight_id}:purge")
    assert r.status_code == 204
    r = client.get(f"/v1/users/user-1/weights/{weight_id}")
    assert r.status_code == 404


def test_weight_response_has_resource_name_and_timestamps(client) -> None:
    """Confirm the response wire shape: ``name`` is the full resource path,
    ``createTime`` / ``updateTime`` are RFC-3339 strings."""
    r = client.post("/v1/users/u-9/weights", json={"weight": 180.0})
    body = r.json()
    assert body["name"].startswith("users/u-9/weights/")
    assert body["createTime"].endswith("Z")
    assert body["updateTime"].endswith("Z")
    # Domain epoch fields are NOT on the wire — only their AIP camelCase
    # counterparts are.
    assert "createdAt" not in body
    assert "updatedAt" not in body
