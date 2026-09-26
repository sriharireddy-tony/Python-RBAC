"""Registration, login, and refresh-token rotation."""

from tests.conftest import API, auth_header, register_tenant


def test_register_creates_tenant_admin_and_system_roles(client):
    body = register_tenant(client, "acme")

    assert body["user"]["email"] == "admin@acme.com"
    assert "password_hash" not in body["user"]
    assert body["tokens"]["token_type"] == "bearer"

    roles = client.get(
        f"{API}/roles", headers=auth_header(body["tokens"]["access_token"])
    ).json()["items"]

    assert {r["name"] for r in roles} == {"Admin", "Manager", "Viewer"}
    assert all(r["is_system_role"] for r in roles)


def test_register_is_atomic_on_duplicate_slug(client):
    register_tenant(client, "acme")

    response = client.post(
        f"{API}/auth/register",
        json={
            "tenant_name": "Acme Again",
            "tenant_slug": "acme",
            "email": "other@acme.com",
            "password": "correct-horse-battery",
        },
    )

    assert response.status_code == 409


def test_login_requires_the_right_tenant(client):
    register_tenant(client, "acme")
    register_tenant(client, "abccorp")

    response = client.post(
        f"{API}/auth/login",
        json={
            "tenant_slug": "abccorp",
            "email": "admin@acme.com",
            "password": "correct-horse-battery",
        },
    )

    assert response.status_code == 401


def test_wrong_password_and_unknown_user_are_indistinguishable(client):
    """Both must return the same code and message, or login becomes a user
    enumeration oracle."""
    register_tenant(client, "acme")

    wrong_password = client.post(
        f"{API}/auth/login",
        json={
            "tenant_slug": "acme",
            "email": "admin@acme.com",
            "password": "wrong-password-here",
        },
    )
    unknown_user = client.post(
        f"{API}/auth/login",
        json={
            "tenant_slug": "acme",
            "email": "nobody@acme.com",
            "password": "correct-horse-battery",
        },
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.json()["detail"] == unknown_user.json()["detail"]


def test_refresh_rotates_the_token(client):
    tenant = register_tenant(client, "acme")
    original = tenant["tokens"]["refresh_token"]

    response = client.post(f"{API}/auth/refresh", json={"refresh_token": original})

    assert response.status_code == 200
    assert response.json()["refresh_token"] != original


def test_reusing_a_rotated_token_revokes_the_whole_family(client):
    """Token theft detection.

    Presenting an already-rotated token means someone captured it. Both the
    attacker and the legitimate user lose the session.
    """
    tenant = register_tenant(client, "acme")
    original = tenant["tokens"]["refresh_token"]

    rotated = client.post(
        f"{API}/auth/refresh", json={"refresh_token": original}
    ).json()["refresh_token"]

    replay = client.post(f"{API}/auth/refresh", json={"refresh_token": original})
    assert replay.status_code == 401
    assert replay.json()["code"] == "token_reuse_detected"

    # The descendant token is now dead too.
    after = client.post(f"{API}/auth/refresh", json={"refresh_token": rotated})
    assert after.status_code == 401


def test_logout_revokes_the_refresh_token(client):
    tenant = register_tenant(client, "acme")
    refresh_token = tenant["tokens"]["refresh_token"]

    assert (
        client.post(f"{API}/auth/logout", json={"refresh_token": refresh_token}).status_code
        == 204
    )
    assert (
        client.post(f"{API}/auth/refresh", json={"refresh_token": refresh_token}).status_code
        == 401
    )


def test_short_password_is_rejected(client):
    response = client.post(
        f"{API}/auth/register",
        json={
            "tenant_name": "Acme",
            "tenant_slug": "acme",
            "email": "admin@acme.com",
            "password": "short",
        },
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
