"""Tenant endpoints.

The unauthenticated list/create endpoints from the first milestone are gone:
- creating a tenant now happens through POST /auth/register, which also
  creates the first admin and the default roles in one transaction;
- listing every tenant was a cross-tenant data leak. A caller may only ever
  see their OWN tenant, identified by the token rather than by a path
  parameter, which removes the possibility of asking for someone else's.
"""

from fastapi import APIRouter, status

from app.core.exceptions import NotFoundError
from app.core.permissions import TENANTS_READ, TENANTS_UPDATE
from app.db.models.tenant import Tenant
from app.db.models.user import User
from app.dependencies.auth import DbSession
from app.dependencies.authorization import require_permission
from app.repositories import tenant_repository
from app.schemas.errors import ErrorResponse
from app.schemas.tenant import TenantRead, TenantUpdate

router = APIRouter(prefix="/tenants", tags=["tenants"])

_FORBIDDEN = {status.HTTP_403_FORBIDDEN: {"model": ErrorResponse}}


def _current_tenant(db: DbSession, tenant_id) -> Tenant:
    tenant = tenant_repository.get_by_id(db, tenant_id)
    if tenant is None:
        raise NotFoundError("Tenant not found")
    return tenant


@router.get(
    "/me",
    response_model=TenantRead,
    responses=_FORBIDDEN,
    summary="The caller's own tenant",
)
def read_my_tenant(
    db: DbSession,
    current_user: User = require_permission(TENANTS_READ),
) -> Tenant:
    return _current_tenant(db, current_user.tenant_id)


@router.patch("/me", response_model=TenantRead, responses=_FORBIDDEN)
def update_my_tenant(
    payload: TenantUpdate,
    db: DbSession,
    current_user: User = require_permission(TENANTS_UPDATE),
) -> Tenant:
    tenant = _current_tenant(db, current_user.tenant_id)

    if payload.name is not None:
        tenant.name = payload.name
    if payload.status is not None:
        tenant.status = payload.status

    db.commit()
    db.refresh(tenant)
    return tenant
