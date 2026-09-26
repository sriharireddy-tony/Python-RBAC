from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models.tenant import Tenant
from app.schemas.common import Page
from app.schemas.errors import ErrorResponse
from app.schemas.tenant import TenantCreate, TenantRead
from app.services import tenant_service

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post(
    "",
    response_model=TenantRead,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
)
def create_tenant(
    payload: TenantCreate,
    db: Session = Depends(get_db),
) -> Tenant:
    return tenant_service.create_tenant(db, payload)


# TODO: admin-only once authentication exists — this currently lists every
# tenant in the system to any caller.
@router.get("", response_model=Page[TenantRead])
def list_tenants(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> Page[TenantRead]:
    items, total = tenant_service.list_tenants(db, skip=skip, limit=limit)
    return Page[TenantRead](
        items=[TenantRead.model_validate(item) for item in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/{tenant_id}",
    response_model=TenantRead,
    responses={status.HTTP_404_NOT_FOUND: {"model": ErrorResponse}},
)
def get_tenant(
    tenant_id: UUID,
    db: Session = Depends(get_db),
) -> Tenant:
    return tenant_service.get_tenant(db, tenant_id)
