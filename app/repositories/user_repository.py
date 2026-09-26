from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.user import User


def _active(stmt):
    """Every read excludes soft-deleted rows. Centralised here so no call
    site has to remember it."""
    return stmt.where(User.deleted_at.is_(None))


def get_by_id(db: Session, tenant_id: UUID, user_id: UUID) -> User | None:
    """Always scoped by tenant.

    tenant_id is a required argument, not an optional filter, so that
    "forgot to scope this query" is impossible rather than merely discouraged.
    """
    stmt = _active(
        select(User).where(User.id == user_id, User.tenant_id == tenant_id)
    )
    return db.execute(stmt).scalar_one_or_none()


def get_by_email(db: Session, tenant_id: UUID, email: str) -> User | None:
    stmt = _active(
        select(User).where(
            User.tenant_id == tenant_id,
            func.lower(User.email) == email.lower(),
        )
    )
    return db.execute(stmt).scalar_one_or_none()


def list_(db: Session, tenant_id: UUID, skip: int = 0, limit: int = 50) -> list[User]:
    stmt = _active(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc(), User.id)
        .offset(skip)
        .limit(limit)
    )
    return list(db.execute(stmt).scalars())


def count(db: Session, tenant_id: UUID) -> int:
    stmt = _active(
        select(func.count()).select_from(User).where(User.tenant_id == tenant_id)
    )
    return db.execute(stmt).scalar_one()


def create(db: Session, user: User) -> User:
    """Stage the INSERT only. The caller owns the transaction."""
    db.add(user)
    db.flush()
    return user
