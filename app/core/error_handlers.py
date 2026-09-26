"""Translate exceptions into the API's single error response shape.

Every failed request — domain error, validation failure, or unhandled crash —
comes back as {"code", "detail", "request_id"}, so clients need exactly one
error branch.
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import (
    AppError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)

# The only place domain errors meet HTTP. app/core/exceptions.py stays
# framework-free because this mapping lives here instead of on the classes.
STATUS_BY_ERROR: dict[type[AppError], int] = {
    NotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    UnauthorizedError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
}


def _status_for(exc: AppError) -> int:
    """Resolve a status code by walking the MRO.

    Same rule Starlette uses to resolve handlers, so a subclass such as
    TenantNotFoundError(NotFoundError) still maps to 404.
    """
    for cls in type(exc).__mro__:
        if cls in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[cls]
    return status.HTTP_400_BAD_REQUEST


def _request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    detail: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "code": code,
            "detail": detail,
            "request_id": _request_id(request),
        },
    )


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    status_code = _status_for(exc)
    logger.warning(
        "app_error code=%s status=%s path=%s request_id=%s detail=%s",
        exc.code,
        status_code,
        request.url.path,
        _request_id(request),
        exc.detail,
    )
    return _error_response(request, status_code, exc.code, exc.detail)


async def handle_http_exception(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Reshape FastAPI's built-in 404/405/etc. into the same envelope."""
    return _error_response(
        request, exc.status_code, "http_error", str(exc.detail)
    )


async def handle_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content={
            "code": "validation_error",
            "detail": "Request validation failed",
            "request_id": _request_id(request),
            "errors": jsonable_encoder(exc.errors()),
        },
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Last resort: log the traceback, return nothing revealing."""
    logger.exception(
        "unhandled_error path=%s request_id=%s",
        request.url.path,
        _request_id(request),
    )
    return _error_response(
        request,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "internal_error",
        "An unexpected error occurred.",
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
