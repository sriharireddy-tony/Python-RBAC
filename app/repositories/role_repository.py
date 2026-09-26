from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.role import Role


def _active(stmt):
    return stmt.where(Role.deleted_at.is_(None))


def get_by_id(db: Session, tenant_id: UUID, role_id: UUID) -> Role | None:
    stmt = _active(select(Role).where(Role.id == role_id, Role.tenant_id == tenant_id))
    return db.execute(stmt).scalar_one_or_none()


def get_by_name(db: Session, tenant_id: UUID, name: str) -> Role | None:
    stmt = _active(select(Role).where(Role.tenant_id == tenant_id, Role.name == name))
    return db.execute(stmt).scalar_one_or_none()


def get_many_by_ids(db: Session, tenant_id: UUID, role_ids: list[UUID]) -> list[Role]:
    """Used to validate role assignment.

    Scoped by tenant so that passing another tenant's role id simply yields
    fewer rows than requested, which the service turns into a 404.
    """
    if not role_ids:
        return []
    stmt = _active(
        select(Role).where(Role.tenant_id == tenant_id, Role.id.in_(role_ids))
    )
    return list(db.execute(stmt).scalars())


def list_(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 50) -> list[Role]:
    stmt = _active(
        select(Role)
        .where(Role.tenant_id == tenant_id)
        .order_by(Role.created_at.desc(), Role.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def count(db: Session, tenant_id: UUID) -> int:
    stmt = _active(
        select(func.count()).select_from(Role).where(Role.tenant_id == tenant_id)
    )
    return db.execute(stmt).scalar_one()


def create(db: Session, role: Role) -> Role:
    db.add(role)
    db.flush()
    return role
