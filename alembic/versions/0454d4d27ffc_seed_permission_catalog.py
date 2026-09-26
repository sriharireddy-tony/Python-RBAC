"""seed permission catalog

Revision ID: 0454d4d27ffc
Revises: c561ce30c917
Create Date: 2026-09-27 00:52:08.982233

A DATA migration, not a schema one. The permission catalog is part of what
the schema means: an empty permissions table makes every authorization check
fail, so this cannot be a script someone remembers to run.

The rows are written literally rather than imported from
app.core.permissions, because a migration must keep producing the same result
years from now even after that module has changed. Migrations are history;
they do not follow the code forward.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0454d4d27ffc"
down_revision: Union[str, Sequence[str], None] = "c561ce30c917"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS: list[tuple[str, str, str]] = [
    ("users", "create", "Create users in the tenant"),
    ("users", "read", "View users in the tenant"),
    ("users", "update", "Modify users in the tenant"),
    ("users", "delete", "Remove users from the tenant"),
    ("roles", "create", "Create roles"),
    ("roles", "read", "View roles"),
    ("roles", "update", "Modify roles and their permissions"),
    ("roles", "delete", "Delete roles"),
    ("permissions", "read", "View the permission catalog"),
    ("tenants", "read", "View the current tenant"),
    ("tenants", "update", "Modify the current tenant"),
]


def upgrade() -> None:
    """Insert the catalog, skipping any row that already exists."""
    connection = op.get_bind()
    for resource, action, description in PERMISSIONS:
        connection.execute(
            sa.text(
                """
                INSERT INTO permissions (id, resource, action, description)
                VALUES (gen_random_uuid(), :resource, :action, :description)
                ON CONFLICT (resource, action) DO NOTHING
                """
            ),
            {"resource": resource, "action": action, "description": description},
        )


def downgrade() -> None:
    """Remove the seeded rows.

    role_permissions has ON DELETE CASCADE, so grants referencing these
    permissions go with them.
    """
    connection = op.get_bind()
    for resource, action, _ in PERMISSIONS:
        connection.execute(
            sa.text(
                "DELETE FROM permissions WHERE resource = :resource AND action = :action"
            ),
            {"resource": resource, "action": action},
        )
