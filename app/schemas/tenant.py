from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.tenant import TenantStatus


class TenantBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")


class TenantCreate(TenantBase):
    pass


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: TenantStatus | None = None


class TenantRead(TenantBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: TenantStatus
    created_at: datetime
    updated_at: datetime
