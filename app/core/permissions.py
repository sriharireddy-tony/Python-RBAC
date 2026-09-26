"""The permission catalog: every action this codebase can perform.

Single source of truth. The seed data migration reads this list, and
require_permission() references these constants -- so a typo is an
ImportError at startup rather than a silent 403 in production.
"""

from typing import NamedTuple


class PermissionDef(NamedTuple):
    resource: str
    action: str
    description: str

    @property
    def code(self) -> str:
        return f"{self.resource}:{self.action}"


USERS_CREATE = PermissionDef("users", "create", "Create users in the tenant")
USERS_READ = PermissionDef("users", "read", "View users in the tenant")
USERS_UPDATE = PermissionDef("users", "update", "Modify users in the tenant")
USERS_DELETE = PermissionDef("users", "delete", "Remove users from the tenant")

ROLES_CREATE = PermissionDef("roles", "create", "Create roles")
ROLES_READ = PermissionDef("roles", "read", "View roles")
ROLES_UPDATE = PermissionDef("roles", "update", "Modify roles and their permissions")
ROLES_DELETE = PermissionDef("roles", "delete", "Delete roles")

PERMISSIONS_READ = PermissionDef("permissions", "read", "View the permission catalog")

TENANTS_READ = PermissionDef("tenants", "read", "View the current tenant")
TENANTS_UPDATE = PermissionDef("tenants", "update", "Modify the current tenant")

ALL_PERMISSIONS: tuple[PermissionDef, ...] = (
    USERS_CREATE,
    USERS_READ,
    USERS_UPDATE,
    USERS_DELETE,
    ROLES_CREATE,
    ROLES_READ,
    ROLES_UPDATE,
    ROLES_DELETE,
    PERMISSIONS_READ,
    TENANTS_READ,
    TENANTS_UPDATE,
)

# Roles created automatically for every new tenant at registration.
# The Admin role receives every permission; the others are useful defaults
# a tenant can edit or delete.
SYSTEM_ROLES: dict[str, tuple[PermissionDef, ...]] = {
    "Admin": ALL_PERMISSIONS,
    "Manager": (USERS_CREATE, USERS_READ, USERS_UPDATE, ROLES_READ, TENANTS_READ),
    "Viewer": (USERS_READ, ROLES_READ, TENANTS_READ),
}

ADMIN_ROLE_NAME = "Admin"
