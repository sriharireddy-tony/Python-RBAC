from typing import Any

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """The single body shape every failed request returns."""

    code: str
    detail: str
    request_id: str | None = None


class ValidationErrorResponse(ErrorResponse):
    """422 responses additionally carry the per-field failures."""

    errors: list[dict[str, Any]]
