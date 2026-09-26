"""Tenant isolation: the bug class you cannot find by clicking around.

Every test here is "tenant A must not see tenant B", and the expected status
is 404 rather than 403 -- a 403 would confirm the resource exists, letting an
attacker enumerate other tenants' ids.
"""

from tests.conftest import API, auth_header, register_tenant


def test_user_cannot_read_another_tenants_user(client):
    a = register_tenant(client, "acme")
    b = register_tenant(client, "abccorp")

    b_user_id = b["user"]["id"]
    a_token = a["tokens"]["access_token"]

    response = client.get(f"{API}/users/{b_user_id}", headers=auth_header(a_token))

    assert response.status_code == 404
    assert response.json()["code"] == "not_found"


def test_user_cannot_update_another_tenants_user(client):
    a = register_tenant(client, "acme")
    b = register_tenant(client, "abccorp")

    response = client.patch(
        f"{API}/users/{b['user']['id']}",
        headers=auth_header(a["tokens"]["access_token"]),
        json={"first_name": "Hacked"},
    )

    assert response.status_code == 404


def test_user_cannot_delete_another_tenants_user(client):
    a = register_tenant(client, "acme")
    b = register_tenant(client, "abccorp")

    response = client.delete(
        f"{API}/users/{b['user']['id']}",
        headers=auth_header(a["tokens"]["access_token"]),
    )

    assert response.status_code == 404


def test_listing_users_returns_only_own_tenant(client):
    a = register_tenant(client, "acme")
    register_tenant(client, "abccorp")

    response = client.get(
        f"{API}/users", headers=auth_header(a["tokens"]["access_token"])
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["tenant_id"] == a["user"]["tenant_id"]


def test_cannot_assign_a_role_from_another_tenant(client):
    """The privilege-escalation case the composite foreign key exists for."""
    a = register_tenant(client, "acme")
    b = register_tenant(client, "abccorp")

    b_roles = client.get(
        f"{API}/roles", headers=auth_header(b["tokens"]["access_token"])
    ).json()["items"]
    b_admin_role_id = next(r["id"] for r in b_roles if r["name"] == "Admin")

    response = client.put(
        f"{API}/users/{a['user']['id']}/roles",
        headers=auth_header(a["tokens"]["access_token"]),
        json=[b_admin_role_id],
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_tenants_me_returns_only_the_callers_tenant(client):
    a = register_tenant(client, "acme")
    register_tenant(client, "abccorp")

    response = client.get(
        f"{API}/tenants/me", headers=auth_header(a["tokens"]["access_token"])
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "acme"


def test_same_email_can_exist_in_two_tenants(client):
    """The consequence of per-tenant email uniqueness: one person, two
    customers. This is why login requires a tenant_slug."""
    a = register_tenant(client, "acme")

    shared_email = "consultant@example.com"
    client.post(
        f"{API}/users",
        headers=auth_header(a["tokens"]["access_token"]),
        json={"email": shared_email, "password": "correct-horse-battery"},
    )

    b = register_tenant(client, "abccorp")
    response = client.post(
        f"{API}/users",
        headers=auth_header(b["tokens"]["access_token"]),
        json={"email": shared_email, "password": "correct-horse-battery"},
    )

    assert response.status_code == 201


def test_duplicate_email_within_one_tenant_is_rejected(client):
    a = register_tenant(client, "acme")
    payload = {"email": "dup@example.com", "password": "correct-horse-battery"}

    first = client.post(
        f"{API}/users", headers=auth_header(a["tokens"]["access_token"]), json=payload
    )
    second = client.post(
        f"{API}/users", headers=auth_header(a["tokens"]["access_token"]), json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["code"] == "conflict"
