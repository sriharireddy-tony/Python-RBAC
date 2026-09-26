from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.models.user import UserStatus
from app.schemas.role import RoleSummary

# Minimum viable password policy. Length beats complexity rules: NIST now
# recommends long passphrases over forced symbol/case mixtures.
PasswordStr = Field(min_length=12, max_length=128)


class UserBase(BaseModel):
    email: EmailStr
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class UserCreate(UserBase):
    """Body for an admin creating a user inside their own tenant.

    Note there is no tenant_id: it comes from the caller's access token, never
    from the request body. Accepting it here would let any authenticated user
    create accounts inside someone else's tenant.
    """

    password: str = PasswordStr
    role_ids: list[UUID] = Field(default_factory=list)


class UserUpdate(BaseModel):
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    status: UserStatus | None = None


class UserRead(UserBase):
    """Outbound shape. password_hash is absent, and that absence is the
    mechanism that keeps it out of responses -- response_model filters."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    status: UserStatus
    is_email_verified: bool
    last_login_at: datetime | None
    created_at: datetime
    updated_at: datetime


class UserWithRoles(UserRead):
    roles: list[RoleSummary]


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = PasswordStr
