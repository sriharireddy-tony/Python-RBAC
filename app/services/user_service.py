from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.db.models.user import User, UserStatus
from app.repositories import user_repository
from app.schemas.user import UserCreate, UserUpdate
from app.services import rbac_service


def create_user(db: Session, tenant_id: UUID, data: UserCreate) -> User:
    if user_repository.get_by_email(db, tenant_id, data.email) is not None:
        raise ConflictError("A user with that email already exists in this tenant")

    user = User(
        tenant_id=tenant_id,
        email=data.email.lower(),
        password_hash=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        status=UserStatus.ACTIVE,
    )

    try:
        user_repository.create(db, user)
        rbac_service.assign_roles(db, user, data.role_ids)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "A user with that email already exists in this tenant"
        ) from exc

    db.refresh(user)
    return user


def get_user(db: Session, tenant_id: UUID, user_id: UUID) -> User:
    """Cross-tenant reads raise NotFound, never Forbidden.

    A 403 would confirm the id exists, letting an attacker enumerate other
    tenants' users. As far as this tenant is concerned, the row does not exist.
    """
    user = user_repository.get_by_id(db, tenant_id, user_id)
    if user is None:
        raise NotFoundError(f"User {user_id} not found")
    return user


def list_users(
    db: Session, tenant_id: UUID, skip: int = 0, limit: int = 50
) -> tuple[list[User], int]:
    return (
        user_repository.list_(db, tenant_id, skip=skip, limit=limit),
        user_repository.count(db, tenant_id),
    )


def update_user(
    db: Session, tenant_id: UUID, user_id: UUID, data: UserUpdate
) -> User:
    user = get_user(db, tenant_id, user_id)

    if data.first_name is not None:
        user.first_name = data.first_name
    if data.last_name is not None:
        user.last_name = data.last_name
    if data.status is not None:
        user.status = data.status

    db.commit()
    db.refresh(user)
    return user


def set_user_roles(
    db: Session, tenant_id: UUID, user_id: UUID, role_ids: list[UUID]
) -> User:
    user = get_user(db, tenant_id, user_id)
    rbac_service.assign_roles(db, user, role_ids)
    db.commit()
    db.refresh(user)
    return user


def delete_user(db: Session, tenant_id: UUID, user_id: UUID) -> None:
    """Soft delete: the row stays so audit history keeps resolving."""
    user = get_user(db, tenant_id, user_id)
    user.deleted_at = datetime.now(UTC)
    db.commit()


def change_password(
    db: Session, user: User, current_password: str, new_password: str
) -> None:
    if not verify_password(current_password, user.password_hash):
        raise ConflictError("Current password is incorrect", code="invalid_password")

    user.password_hash = hash_password(new_password)
    db.commit()
