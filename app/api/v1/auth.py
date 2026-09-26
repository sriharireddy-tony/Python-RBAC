from fastapi import APIRouter, status

from app.dependencies.auth import CurrentUser, DbSession
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
)
from app.schemas.errors import ErrorResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"model": ErrorResponse}},
    summary="Create a new tenant and its first Admin user",
)
def register(payload: RegisterRequest, db: DbSession) -> AuthResponse:
    user, tokens = auth_service.register(db, payload)
    return AuthResponse(user=user, tokens=tokens)


@router.post(
    "/login",
    response_model=AuthResponse,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
)
def login(payload: LoginRequest, db: DbSession) -> AuthResponse:
    user, tokens = auth_service.login(db, payload)
    return AuthResponse(user=user, tokens=tokens)


@router.post(
    "/refresh",
    response_model=TokenPair,
    responses={status.HTTP_401_UNAUTHORIZED: {"model": ErrorResponse}},
    summary="Rotate a refresh token",
)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPair:
    _, tokens = auth_service.refresh(db, payload.refresh_token)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: LogoutRequest, db: DbSession) -> None:
    auth_service.logout(db, payload.refresh_token)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke every session for the current user",
)
def logout_all(current_user: CurrentUser, db: DbSession) -> None:
    auth_service.logout_all(db, current_user)
