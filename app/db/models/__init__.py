"""Import every model here so it registers itself on Base.metadata.

Alembic's autogenerate only sees tables whose modules have been imported.
A model missing from this list is silently absent from migrations.
"""

from app.db.models.associations import role_permissions, user_roles
from app.db.models.permission import Permission
from app.db.models.refresh_token import RefreshToken
from app.db.models.role import Role
from app.db.models.tenant import Tenant, TenantStatus
from app.db.models.user import User, UserStatus

__all__ = [
    "Permission",
    "RefreshToken",
    "Role",
    "Tenant",
    "TenantStatus",
    "User",
    "UserStatus",
    "role_permissions",
    "user_roles",
]
