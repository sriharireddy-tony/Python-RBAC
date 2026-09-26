import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError, UnauthorizedError
from app.core.permissions import ADMIN_ROLE_NAME
from app.core.security import (
    REFRESH_TOKEN_TYPE,
    create_access_token,
    create_refresh_token,
    generate_opaque_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.models.refresh_token import RefreshToken
from app.db.models.tenant import Tenant, TenantStatus
from app.db.models.user import User, UserStatus
from app.repositories import (
    refresh_token_repository,
    tenant_repository,
    user_repository,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenPair
from app.services import rbac_service

# Deliberately identical for "no such tenant", "no such user" and "wrong
# password". Distinguishing them turns the login endpoint into a user
# enumeration oracle.
_INVALID_CREDENTIALS = "Invalid credentials"


def register(db: Session, data: RegisterRequest) -> tuple[User, TokenPair]:
    """Create a tenant, its Admin user, and the default roles.

    Five writes, ONE transaction. A partial failure here would otherwise
    leave an orphaned tenant whose admin has no admin role -- an account
    nobody can get into and nobody can clean up.
    """
    if tenant_repository.get_by_slug(db, data.tenant_slug) is not None:
        raise ConflictError(f"Tenant with slug '{data.tenant_slug}' already exists")

    try:
        tenant = Tenant(
            name=data.tenant_name,
            slug=data.tenant_slug,
            status=TenantStatus.ACTIVE,
        )
        tenant_repository.create(db, tenant)

        roles = rbac_service.provision_system_roles(db, tenant.id)

        user = User(
            tenant_id=tenant.id,
            email=data.email.lower(),
            password_hash=hash_password(data.password),
            first_name=data.first_name,
            last_name=data.last_name,
            status=UserStatus.ACTIVE,
        )
        user_repository.create(db, user)

        user.roles = [roles[ADMIN_ROLE_NAME]]
        db.flush()

        tokens = _issue_token_pair(db, user, family_id=uuid.uuid4())
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("Tenant or user already exists") from exc

    db.refresh(user)
    return user, tokens


def login(db: Session, data: LoginRequest) -> tuple[User, TokenPair]:
    tenant = tenant_repository.get_by_slug(db, data.tenant_slug)
    if tenant is None or tenant.status is not TenantStatus.ACTIVE:
        raise UnauthorizedError(_INVALID_CREDENTIALS)

    user = user_repository.get_by_email(db, tenant.id, data.email)
    if user is None:
        # Hash anyway so a missing user and a wrong password take the same
        # time. Otherwise response latency reveals which emails are registered.
        hash_password(data.password)
        raise UnauthorizedError(_INVALID_CREDENTIALS)

    if not verify_password(data.password, user.password_hash):
        raise UnauthorizedError(_INVALID_CREDENTIALS)

    if user.status is not UserStatus.ACTIVE:
        raise UnauthorizedError("This account is not active")

    user.last_login_at = datetime.now(UTC)
    tokens = _issue_token_pair(db, user, family_id=uuid.uuid4())
    db.commit()
    db.refresh(user)
    return user, tokens


def refresh(db: Session, refresh_token: str) -> tuple[User, TokenPair]:
    """Rotate a refresh token, with reuse detection.

    Each refresh mints a new token and revokes the one presented. If an
    ALREADY revoked token shows up, it was captured by someone -- we cannot
    tell whether the caller is the attacker or the victim, so the entire
    family is revoked and both must log in again.
    """
    stored = refresh_token_repository.get_by_hash(db, hash_token(refresh_token))
    if stored is None:
        raise UnauthorizedError("Invalid refresh token")

    if stored.revoked_at is not None:
        refresh_token_repository.revoke_family(db, stored.family_id)
        db.commit()
        raise UnauthorizedError(
            "Refresh token has already been used; all sessions have been revoked",
            code="token_reuse_detected",
        )

    if stored.expires_at <= datetime.now(UTC):
        raise UnauthorizedError("Refresh token has expired")

    user = db.get(User, stored.user_id)
    if user is None or user.deleted_at is not None or user.status is not UserStatus.ACTIVE:
        raise UnauthorizedError("Account is no longer active")

    refresh_token_repository.revoke(db, stored)
    tokens = _issue_token_pair(db, user, family_id=stored.family_id)
    db.commit()
    db.refresh(user)
    return user, tokens


def logout(db: Session, refresh_token: str) -> None:
    """Idempotent on purpose: logging out twice is not an error, and telling
    the caller their token was unknown leaks information."""
    stored = refresh_token_repository.get_by_hash(db, hash_token(refresh_token))
    if stored is not None and stored.revoked_at is None:
        refresh_token_repository.revoke(db, stored)
        db.commit()


def logout_all(db: Session, user: User) -> int:
    revoked = refresh_token_repository.revoke_all_for_user(db, user.id)
    db.commit()
    return revoked


def _issue_token_pair(db: Session, user: User, *, family_id: uuid.UUID) -> TokenPair:
    access_token = create_access_token(user_id=user.id, tenant_id=user.tenant_id)

    # The refresh token is opaque random bytes wrapped in a JWT for transport.
    # Only its SHA-256 hash is persisted, so a database leak yields no usable
    # sessions -- the same reasoning as password hashing.
    raw_refresh = generate_opaque_token()
    expires_at = datetime.now(UTC) + timedelta(
        days=settings.refresh_token_expire_days
    )

    refresh_token_repository.create(
        db,
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(raw_refresh),
            family_id=family_id,
            expires_at=expires_at,
        ),
    )

    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


__all__ = [
    "REFRESH_TOKEN_TYPE",
    "login",
    "logout",
    "logout_all",
    "refresh",
    "register",
]
