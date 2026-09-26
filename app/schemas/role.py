from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.permission import PermissionRead


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)


class RoleCreate(RoleBase):
    permission_ids: list[UUID] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=255)
    # None means "leave permissions alone"; [] means "remove them all".
    permission_ids: list[UUID] | None = None


class RoleSummary(BaseModel):
    """Nested inside user responses -- no permission list, to keep payloads small."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    is_system_role: bool


class RoleRead(RoleBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    is_system_role: bool
    permissions: list[PermissionRead]
    created_at: datetime
    updated_at: datetime
