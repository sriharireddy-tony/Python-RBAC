from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.permission import Permission
from app.db.models.role import Role
from app.db.models.user import User


def list_all(db: Session) -> list[Permission]:
    """Permissions are a global catalog, so this needs no tenant scope."""
    stmt = select(Permission).order_by(Permission.resource, Permission.action)
    return list(db.execute(stmt).scalars())


def get_many_by_ids(db: Session, permission_ids: list[UUID]) -> list[Permission]:
    if not permission_ids:
        return []
    stmt = select(Permission).where(Permission.id.in_(permission_ids))
    return list(db.execute(stmt).scalars())


def get_codes_for_user(db: Session, user_id: UUID) -> set[str]:
    """Resolve user -> roles -> permissions in ONE query.

    The naive version (load user, loop roles, loop permissions) issues a
    query per role on every single authorized request. This is a two-join
    select returning just the two columns needed.
    """
    stmt = (
        select(Permission.resource, Permission.action)
        .join(Permission.roles)
        .join(Role.users)
        .where(
            User.id == user_id,
            Role.deleted_at.is_(None),
        )
        .distinct()
    )
    return {f"{resource}:{action}" for resource, action in db.execute(stmt).all()}
