from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.permissions import (
    USERS_CREATE,
    USERS_DELETE,
    USERS_READ,
    USERS_UPDATE,
)
from app.db.models.user import User
from app.dependencies.auth import CurrentUser, DbSession
from app.dependencies.authorization import require_permission
from app.schemas.common import Page
from app.schemas.errors import ErrorResponse
from app.schemas.user import (
    PasswordChange,
    UserCreate,
    UserRead,
    UserUpdate,
    UserWithRoles,
)
from app.services import rbac_service, user_service

router = APIRouter(prefix="/users", tags=["users"])

_FORBIDDEN = {status.HTTP_403_FORBIDDEN: {"model": ErrorResponse}}
_NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}


# /me is declared before /{user_id} so the literal path wins the match --
# otherwise "me" would be parsed as a user_id and fail UUID validation.
@router.get("/me", response_model=dict, summary="The authenticated user")
def read_me(current_user: CurrentUser, db: DbSession) -> dict:
    permissions = sorted(rbac_service.get_user_permission_codes(db, current_user.id))
    return {
        **UserRead.model_validate(current_user).model_dump(mode="json"),
        "roles": [role.name for role in current_user.roles],
        "permissions": permissions,
    }


@router.post(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Change your own password",
)
def change_my_password(
    payload: PasswordChange, current_user: CurrentUser, db: DbSession
) -> None:
    user_service.change_password(
        db, current_user, payload.current_password, payload.new_password
    )


@router.post(
    "",
    response_model=UserWithRoles,
    status_code=status.HTTP_201_CREATED,
    responses=_FORBIDDEN | {status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
def create_user(
    payload: UserCreate,
    db: DbSession,
    current_user: User = require_permission(USERS_CREATE),
) -> User:
    # tenant_id comes from the token, never from the body.
    return user_service.create_user(db, current_user.tenant_id, payload)


@router.get("", response_model=Page[UserWithRoles], responses=_FORBIDDEN)
def list_users(
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = require_permission(USERS_READ),
) -> Page[UserWithRoles]:
    items, total = user_service.list_users(
        db, current_user.tenant_id, skip=skip, limit=limit
    )
    return Page[UserWithRoles](
        items=[UserWithRoles.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{user_id}", response_model=UserWithRoles, responses=_FORBIDDEN | _NOT_FOUND
)
def get_user(
    user_id: UUID,
    db: DbSession,
    current_user: User = require_permission(USERS_READ),
) -> User:
    return user_service.get_user(db, current_user.tenant_id, user_id)


@router.patch(
    "/{user_id}", response_model=UserWithRoles, responses=_FORBIDDEN | _NOT_FOUND
)
def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: DbSession,
    current_user: User = require_permission(USERS_UPDATE),
) -> User:
    return user_service.update_user(db, current_user.tenant_id, user_id, payload)


@router.put(
    "/{user_id}/roles",
    response_model=UserWithRoles,
    responses=_FORBIDDEN | _NOT_FOUND,
    summary="Replace a user's roles",
)
def set_user_roles(
    user_id: UUID,
    role_ids: list[UUID],
    db: DbSession,
    current_user: User = require_permission(USERS_UPDATE),
) -> User:
    return user_service.set_user_roles(db, current_user.tenant_id, user_id, role_ids)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_FORBIDDEN | _NOT_FOUND,
)
def delete_user(
    user_id: UUID,
    db: DbSession,
    current_user: User = require_permission(USERS_DELETE),
) -> None:
    user_service.delete_user(db, current_user.tenant_id, user_id)
