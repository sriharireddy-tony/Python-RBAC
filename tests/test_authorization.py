"""The role x endpoint permission matrix.

This is the suite that cannot be replaced by clicking through Swagger: the
number of combinations grows with roles x endpoints, and a single wrong
answer is a privilege-escalation bug.
"""

import pytest

from tests.conftest import API, auth_header, create_user_with_role, register_tenant

# (role, method, path, expected status). 403 means the permission check
# denied it; anything else means it got through to the endpoint.
MATRIX = [
    # Admin holds every permission.
    ("Admin", "GET", "/users", 200),
    ("Admin", "GET", "/roles", 200),
    ("Admin", "GET", "/permissions", 200),
    ("Admin", "GET", "/tenants/me", 200),
    # Manager may read and write users, but not touch roles.
    ("Manager", "GET", "/users", 200),
    ("Manager", "GET", "/roles", 200),
    ("Manager", "POST", "/roles", 403),
    ("Manager", "GET", "/permissions", 403),
    ("Manager", "GET", "/tenants/me", 200),
    # Viewer is read-only.
    ("Viewer", "GET", "/users", 200),
    ("Viewer", "POST", "/users", 403),
    ("Viewer", "GET", "/roles", 200),
    ("Viewer", "POST", "/roles", 403),
    ("Viewer", "GET", "/permissions", 403),
]


@pytest.mark.parametrize("role_name,method,path,expected", MATRIX)
def test_permission_matrix(client, role_name, method, path, expected):
    tenant = register_tenant(client, "acme")
    admin_token = tenant["tokens"]["access_token"]

    if role_name == "Admin":
        token = admin_token
    else:
        token = create_user_with_role(client, admin_token, role_name, "acme")

    response = client.request(
        method,
        f"{API}{path}",
        headers=auth_header(token),
        json={} if method in {"POST", "PATCH", "PUT"} else None,
    )

    if expected == 403:
        assert response.status_code == 403, (
            f"{role_name} should NOT be able to {method} {path}"
        )
        assert response.json()["code"] == "permission_denied"
    else:
        assert response.status_code != 403, (
            f"{role_name} SHOULD be able to {method} {path}"
        )


def test_no_token_is_401_not_403(client):
    response = client.get(f"{API}/users")
    assert response.status_code == 401
    assert response.json()["code"] == "unauthorized"


def test_garbage_token_is_401(client):
    response = client.get(f"{API}/users", headers=auth_header("not-a-jwt"))
    assert response.status_code == 401


def test_refresh_token_is_rejected_as_an_access_token(client):
    """A refresh token is a validly signed JWT. Without the token_type check
    it would work as an access token and defeat the short access lifetime."""
    tenant = register_tenant(client, "acme")
    refresh = tenant["tokens"]["refresh_token"]

    response = client.get(f"{API}/users", headers=auth_header(refresh))

    assert response.status_code == 401


def test_permission_revocation_takes_effect_immediately(client):
    """The payoff for keeping permissions OUT of the JWT.

    The token is unchanged and unexpired; removing the role still locks the
    user out on the very next request.
    """
    tenant = register_tenant(client, "acme")
    admin_token = tenant["tokens"]["access_token"]
    viewer_token = create_user_with_role(client, admin_token, "Viewer", "acme")

    assert client.get(f"{API}/users", headers=auth_header(viewer_token)).status_code == 200

    viewer = client.get(f"{API}/users/me", headers=auth_header(viewer_token)).json()
    client.put(
        f"{API}/users/{viewer['id']}/roles",
        headers=auth_header(admin_token),
        json=[],
    )

    assert client.get(f"{API}/users", headers=auth_header(viewer_token)).status_code == 403


def test_me_reports_roles_and_permissions(client):
    tenant = register_tenant(client, "acme")
    token = tenant["tokens"]["access_token"]

    body = client.get(f"{API}/users/me", headers=auth_header(token)).json()

    assert body["roles"] == ["Admin"]
    assert "users:delete" in body["permissions"]
    assert "password_hash" not in body


def test_system_role_cannot_be_deleted(client):
    """Otherwise a tenant could delete its own Admin role and lock everyone out."""
    tenant = register_tenant(client, "acme")
    token = tenant["tokens"]["access_token"]

    roles = client.get(f"{API}/roles", headers=auth_header(token)).json()["items"]
    admin_role_id = next(r["id"] for r in roles if r["name"] == "Admin")

    response = client.delete(f"{API}/roles/{admin_role_id}", headers=auth_header(token))

    assert response.status_code == 403
