"""Authorization: is this caller allowed to do this?

``require_permission`` is a dependency FACTORY -- calling it returns a
dependency function closed over the required permission code. That is what
lets each route declare its own requirement declaratively:

    @router.delete("/{user_id}", dependencies=[require_permission(USERS_DELETE)])

The check runs before the endpoint body, so an unauthorized request never
reaches the code that would touch data.
"""

from collections.abc import Callable

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.exceptions import PermissionDeniedError
from app.core.permissions import PermissionDef
from app.db.database import get_db
from app.db.models.user import User
from app.dependencies.auth import get_current_user
from app.services import rbac_service


def require_permission(permission: PermissionDef | str) -> Depends:
    """Build a dependency that denies the request without `permission`.

    Takes a PermissionDef rather than a bare string wherever possible: a
    typo'd constant is an ImportError at startup, while a typo'd string is a
    permission nobody holds -- a 403 that only shows up in production.
    """
    code = permission.code if isinstance(permission, PermissionDef) else permission

    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        if not rbac_service.user_has_permission(db, current_user.id, code):
            # The detail names the permission, not the resource: telling the
            # caller which permission they lack is useful and leaks nothing.
            raise PermissionDeniedError(f"Missing required permission: {code}")
        return current_user

    return Depends(dependency)


def require_any_permission(*permissions: PermissionDef | str) -> Depends:
    """Allow the request if the caller holds ANY of the listed permissions."""
    codes = {p.code if isinstance(p, PermissionDef) else p for p in permissions}

    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> User:
        held = rbac_service.get_user_permission_codes(db, current_user.id)
        if not (held & codes):
            raise PermissionDeniedError(
                f"Missing any of the required permissions: {', '.join(sorted(codes))}"
            )
        return current_user

    return Depends(dependency)


PermissionChecker = Callable[..., User]
