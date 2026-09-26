import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.database import SessionLocal
from app.main import app

API = "/api/v1"


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_db() -> Iterator[None]:
    """Truncate tenant data between tests, leaving the seeded catalog alone.

    Permissions are NOT truncated: they are reference data owned by a
    migration, not test fixtures.
    """
    yield
    db = SessionLocal()
    try:
        db.execute(
            text(
                "TRUNCATE user_roles, role_permissions, refresh_tokens, "
                "users, roles, tenants CASCADE"
            )
        )
        db.commit()
    finally:
        db.close()


def register_tenant(client: TestClient, slug: str | None = None) -> dict:
    """Create a tenant with its Admin user and return the parsed response."""
    slug = slug or f"t-{uuid.uuid4().hex[:8]}"
    response = client.post(
        f"{API}/auth/register",
        json={
            "tenant_name": slug.title(),
            "tenant_slug": slug,
            "email": f"admin@{slug}.com",
            "password": "correct-horse-battery",
            "first_name": "Ada",
            "last_name": "Admin",
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    body["slug"] = slug
    return body


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def create_user_with_role(
    client: TestClient, admin_token: str, role_name: str, slug: str
) -> str:
    """Create a user holding exactly one of the seeded system roles and log in."""
    roles = client.get(f"{API}/roles", headers=auth_header(admin_token)).json()["items"]
    role_id = next(r["id"] for r in roles if r["name"] == role_name)

    email = f"{role_name.lower()}-{uuid.uuid4().hex[:6]}@{slug}.com"
    response = client.post(
        f"{API}/users",
        headers=auth_header(admin_token),
        json={
            "email": email,
            "password": "correct-horse-battery",
            "role_ids": [role_id],
        },
    )
    assert response.status_code == 201, response.text

    login = client.post(
        f"{API}/auth/login",
        json={
            "tenant_slug": slug,
            "email": email,
            "password": "correct-horse-battery",
        },
    )
    assert login.status_code == 200, login.text
    return login.json()["tokens"]["access_token"]
