class AppError(Exception):
    """Base class for domain errors raised by the service layer."""


class NotFoundError(AppError):
    """A requested resource does not exist."""


class ConflictError(AppError):
    """The request conflicts with existing state (e.g. a duplicate unique field)."""