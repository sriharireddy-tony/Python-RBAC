from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import SYSTEM_ROLES
from app.db.models.permission import Permission
from app.db.models.role import Role
from app.db.models.user import User
from app.repositories import permission_repository, role_repository


def get_user_permission_codes(db: Session, user_id: UUID) -> set[str]:
    return permission_repository.get_codes_for_user(db, user_id)


def user_has_permission(db: Session, user_id: UUID, code: str) -> bool:
    return code in get_user_permission_codes(db, user_id)


def list_permissions(db: Session) -> list[Permission]:
    return permission_repository.list_all(db)


def provision_system_roles(db: Session, tenant_id: UUID) -> dict[str, Role]:
    """Create the default roles for a brand-new tenant.

    Staged only -- the caller commits, so tenant + user + roles + assignment
    land as a single transaction.
    """
    catalog = {p.code: p for p in permission_repository.list_all(db)}
    created: dict[str, Role] = {}

    for role_name, permission_defs in SYSTEM_ROLES.items():
        role = Role(
            tenant_id=tenant_id,
            name=role_name,
            description=f"Default {role_name} role",
            is_system_role=True,
        )
        role.permissions = [
            catalog[pdef.code] for pdef in permission_defs if pdef.code in catalog
        ]
        role_repository.create(db, role)
        created[role_name] = role

    return created


def assign_roles(db: Session, user: User, role_ids: list[UUID]) -> None:
    """Replace a user's roles.

    Roles are looked up scoped to the user's own tenant, so an id belonging
    to another tenant simply is not found -- the composite foreign key on
    user_roles is the second line of defence behind this check.
    """
    if not role_ids:
        user.roles = []
        db.flush()
        return

    roles = role_repository.get_many_by_ids(db, user.tenant_id, role_ids)
    found = {role.id for role in roles}
    missing = [str(rid) for rid in role_ids if rid not in found]
    if missing:
        raise NotFoundError(f"Role(s) not found: {', '.join(missing)}")

    user.roles = roles
    db.flush()


def create_role(
    db: Session, tenant_id: UUID, name: str, description: str | None,
    permission_ids: list[UUID],
) -> Role:
    if role_repository.get_by_name(db, tenant_id, name) is not None:
        raise ConflictError(f"Role '{name}' already exists in this tenant")

    role = Role(tenant_id=tenant_id, name=name, description=description)
    role.permissions = _resolve_permissions(db, permission_ids)
    role_repository.create(db, role)
    db.commit()
    db.refresh(role)
    return role


def get_role(db: Session, tenant_id: UUID, role_id: UUID) -> Role:
    role = role_repository.get_by_id(db, tenant_id, role_id)
    if role is None:
        raise NotFoundError(f"Role {role_id} not found")
    return role


def list_roles(
    db: Session, tenant_id: UUID, skip: int = 0, limit: int = 50
) -> tuple[list[Role], int]:
    return (
        role_repository.list_(db, tenant_id, skip=skip, limit=limit),
        role_repository.count(db, tenant_id),
    )


def update_role(
    db: Session,
    tenant_id: UUID,
    role_id: UUID,
    *,
    name: str | None = None,
    description: str | None = None,
    permission_ids: list[UUID] | None = None,
) -> Role:
    role = get_role(db, tenant_id, role_id)

    if name is not None and name != role.name:
        if role_repository.get_by_name(db, tenant_id, name) is not None:
            raise ConflictError(f"Role '{name}' already exists in this tenant")
        role.name = name

    if description is not None:
        role.description = description

    # None means "leave alone"; [] means "clear them".
    if permission_ids is not None:
        role.permissions = _resolve_permissions(db, permission_ids)

    db.commit()
    db.refresh(role)
    return role


def delete_role(db: Session, tenant_id: UUID, role_id: UUID) -> None:
    role = get_role(db, tenant_id, role_id)

    # Without this a tenant could delete its own Admin role and lock every
    # user out of the account permanently.
    if role.is_system_role:
        raise PermissionDeniedError(f"Role '{role.name}' is a system role and cannot be deleted")

    from datetime import UTC, datetime

    role.deleted_at = datetime.now(UTC)
    db.commit()


def _resolve_permissions(db: Session, permission_ids: list[UUID]) -> list[Permission]:
    permissions = permission_repository.get_many_by_ids(db, permission_ids)
    found = {p.id for p in permissions}
    missing = [str(pid) for pid in permission_ids if pid not in found]
    if missing:
        raise NotFoundError(f"Permission(s) not found: {', '.join(missing)}")
    return permissions
