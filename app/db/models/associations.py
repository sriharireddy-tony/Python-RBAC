"""Join tables for the many-to-many RBAC relationships.

``user_roles`` carries ``tenant_id`` and uses COMPOSITE foreign keys. Plain
``user_id``/``role_id`` FKs would happily accept tenant A's user paired with
tenant B's role -- a cross-tenant privilege escalation that only application
discipline would prevent. With composite FKs the database rejects it, so the
invariant holds even for a buggy service or a manual psql insert.

``role_permissions`` needs no tenant_id: permissions are a global catalog of
what the software can do, and roles are already tenant-scoped.
"""

from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Table, func

from app.db.database import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("tenant_id", ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True),
    Column("user_id", primary_key=True),
    Column("role_id", primary_key=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    ForeignKeyConstraint(
        ["tenant_id", "user_id"],
        ["users.tenant_id", "users.id"],
        ondelete="CASCADE",
        name="fk_user_roles_tenant_user",
    ),
    ForeignKeyConstraint(
        ["tenant_id", "role_id"],
        ["roles.tenant_id", "roles.id"],
        ondelete="CASCADE",
        name="fk_user_roles_tenant_role",
    ),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
)
