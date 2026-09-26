from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.user import PasswordStr, UserRead


class RegisterRequest(BaseModel):
    """Creates a brand-new tenant and its first Admin user in one call."""

    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    email: EmailStr
    password: str = PasswordStr
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)


class LoginRequest(BaseModel):
    """tenant_slug is required because email is only unique within a tenant.

    The same person can hold accounts at several customers, so email alone
    does not identify a user.
    """

    tenant_slug: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(BaseModel):
    user: UserRead
    tokens: TokenPair


class CurrentUserResponse(UserRead):
    """/users/me -- identity plus the resolved permission codes, so a
    frontend can hide controls the user cannot use."""

    roles: list[str]
    permissions: list[str]
