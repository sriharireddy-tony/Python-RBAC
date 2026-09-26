from uuid import UUID

from fastapi import APIRouter, Query, status

from app.core.permissions import (
    PERMISSIONS_READ,
    ROLES_CREATE,
    ROLES_DELETE,
    ROLES_READ,
    ROLES_UPDATE,
)
from app.db.models.role import Role
from app.db.models.user import User
from app.dependencies.auth import DbSession
from app.dependencies.authorization import require_permission
from app.schemas.common import Page
from app.schemas.errors import ErrorResponse
from app.schemas.permission import PermissionRead
from app.schemas.role import RoleCreate, RoleRead, RoleUpdate
from app.services import rbac_service

router = APIRouter(tags=["roles"])

_FORBIDDEN = {status.HTTP_403_FORBIDDEN: {"model": ErrorResponse}}
_NOT_FOUND = {status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}}


@router.get(
    "/permissions",
    response_model=list[PermissionRead],
    responses=_FORBIDDEN,
    summary="The global permission catalog",
)
def list_permissions(
    db: DbSession,
    current_user: User = require_permission(PERMISSIONS_READ),
) -> list:
    # No tenant scope: permissions describe what the software can do, which
    # is identical for every customer.
    return rbac_service.list_permissions(db)


@router.post(
    "/roles",
    response_model=RoleRead,
    status_code=status.HTTP_201_CREATED,
    responses=_FORBIDDEN | {status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
def create_role(
    payload: RoleCreate,
    db: DbSession,
    current_user: User = require_permission(ROLES_CREATE),
) -> Role:
    return rbac_service.create_role(
        db,
        current_user.tenant_id,
        name=payload.name,
        description=payload.description,
        permission_ids=payload.permission_ids,
    )


@router.get("/roles", response_model=Page[RoleRead], responses=_FORBIDDEN)
def list_roles(
    db: DbSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = require_permission(ROLES_READ),
) -> Page[RoleRead]:
    items, total = rbac_service.list_roles(
        db, current_user.tenant_id, skip=skip, limit=limit
    )
    return Page[RoleRead](
        items=[RoleRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/roles/{role_id}", response_model=RoleRead, responses=_FORBIDDEN | _NOT_FOUND)
def get_role(
    role_id: UUID,
    db: DbSession,
    current_user: User = require_permission(ROLES_READ),
) -> Role:
    return rbac_service.get_role(db, current_user.tenant_id, role_id)


@router.patch(
    "/roles/{role_id}", response_model=RoleRead, responses=_FORBIDDEN | _NOT_FOUND
)
def update_role(
    role_id: UUID,
    payload: RoleUpdate,
    db: DbSession,
    current_user: User = require_permission(ROLES_UPDATE),
) -> Role:
    return rbac_service.update_role(
        db,
        current_user.tenant_id,
        role_id,
        name=payload.name,
        description=payload.description,
        permission_ids=payload.permission_ids,
    )


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=_FORBIDDEN | _NOT_FOUND,
)
def delete_role(
    role_id: UUID,
    db: DbSession,
    current_user: User = require_permission(ROLES_DELETE),
) -> None:
    rbac_service.delete_role(db, current_user.tenant_id, role_id)
