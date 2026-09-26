from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.tenant import Tenant


def get_by_id(db: Session, tenant_id: UUID) -> Tenant | None:
    stmt = select(Tenant).where(Tenant.id == tenant_id)
    return db.execute(stmt).scalar_one_or_none()


def get_by_slug(db: Session, slug: str) -> Tenant | None:
    stmt = select(Tenant).where(Tenant.slug == slug)
    return db.execute(stmt).scalar_one_or_none()


def list_(db: Session, skip: int = 0, limit: int = 50) -> list[Tenant]:
    stmt = (
        select(Tenant)
        .order_by(Tenant.created_at.desc(), Tenant.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def count(db: Session) -> int:
    stmt = select(func.count()).select_from(Tenant)
    return db.execute(stmt).scalar_one()


def create(db: Session, tenant: Tenant) -> Tenant:
    """Stage the INSERT only. The caller owns the transaction."""
    db.add(tenant)
    db.flush()
    return tenant
