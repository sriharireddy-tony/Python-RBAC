"""Domain errors raised by the service layer.

Deliberately free of any HTTP or FastAPI imports: services must stay callable
from a CLI command, a background worker, or a test. Turning these into HTTP
responses is the job of ``app.core.error_handlers``.
"""


class AppError(Exception):
    """Base class for domain errors raised by the service layer.

    ``code`` is the stable, machine-readable identifier clients branch on.
    ``detail`` is the human-readable message and may be reworded at any time,
    so clients must never parse it.
    """

    code = "app_error"

    def __init__(self, detail: str, *, code: str | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        if code is not None:
            self.code = code

    def __str__(self) -> str:
        return self.detail


class NotFoundError(AppError):
    """A requested resource does not exist."""

    code = "not_found"


class ConflictError(AppError):
    """The request conflicts with existing state (e.g. a duplicate unique field)."""

    code = "conflict"


class UnauthorizedError(AppError):
    """The caller could not be authenticated."""

    code = "unauthorized"


class PermissionDeniedError(AppError):
    """The caller is authenticated but not allowed to perform this action."""

    code = "permission_denied"
