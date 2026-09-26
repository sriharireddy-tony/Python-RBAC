from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.models.refresh_token import RefreshToken


def get_by_hash(db: Session, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    return db.execute(stmt).scalar_one_or_none()


def create(db: Session, token: RefreshToken) -> RefreshToken:
    db.add(token)
    db.flush()
    return token


def revoke(db: Session, token: RefreshToken) -> None:
    token.revoked_at = datetime.now(UTC)
    db.flush()


def revoke_family(db: Session, family_id: UUID) -> int:
    """Revoke every live token descended from one login.

    Called when a already-revoked token is replayed, which means it was
    stolen: the legitimate user and the attacker both lose the session, and
    the user simply logs in again.
    """
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    return db.execute(stmt).rowcount


def revoke_all_for_user(db: Session, user_id: UUID) -> int:
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )
    return db.execute(stmt).rowcount
