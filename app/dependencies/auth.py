"""Authentication: who is calling?

Turns a bearer token into a User row, or raises. Says nothing about what
that user is allowed to do -- that is authorization, in the sibling module.
"""

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.security import ACCESS_TOKEN_TYPE, decode_token
from app.db.database import get_db
from app.db.models.user import User, UserStatus
from app.repositories import user_repository

# auto_error=False so a missing header raises OUR UnauthorizedError through
# the normal handler, instead of Starlette's differently-shaped 403.
_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    if credentials is None:
        raise UnauthorizedError("Not authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Access token has expired", code="token_expired") from exc
    except jwt.PyJWTError as exc:
        raise UnauthorizedError("Invalid access token") from exc

    # A refresh token is also a validly signed JWT. Without this check it
    # would be accepted as an access token, silently defeating the short
    # access-token lifetime.
    if payload.get("token_type") != ACCESS_TOKEN_TYPE:
        raise UnauthorizedError("Invalid token type")

    try:
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenant_id"])
    except (KeyError, ValueError) as exc:
        raise UnauthorizedError("Malformed access token") from exc

    # Scoped by the tenant_id from the token, so a token cannot be used to
    # reach a user in a different tenant even if the ids were tampered with
    # (they cannot be -- the signature covers them -- but defence in depth).
    user = user_repository.get_by_id(db, tenant_id, user_id)
    if user is None:
        raise UnauthorizedError("Account no longer exists")

    if user.status is not UserStatus.ACTIVE:
        raise UnauthorizedError("This account is not active")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
DbSession = Annotated[Session, Depends(get_db)]
