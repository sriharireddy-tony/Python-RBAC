from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.db.models.tenant import Tenant
from app.repositories import tenant_repository
from app.schemas.tenant import TenantCreate


def create_tenant(db: Session, data: TenantCreate) -> Tenant:
    if tenant_repository.get_by_slug(db, data.slug) is not None:
        raise ConflictError(f"Tenant with slug '{data.slug}' already exists")

    tenant = Tenant(name=data.name, slug=data.slug)

    try:
        tenant_repository.create(db, tenant)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(f"Tenant with slug '{data.slug}' already exists") from exc

    db.refresh(tenant)
    return tenant


def get_tenant(db: Session, tenant_id: UUID) -> Tenant:
    tenant = tenant_repository.get_by_id(db, tenant_id)
    if tenant is None:
        raise NotFoundError(f"Tenant {tenant_id} not found")
    return tenant


def list_tenants(db: Session, skip: int = 0, limit: int = 50) -> list[Tenant]:
    return tenant_repository.list_(db, skip=skip, limit=limit)