from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Envelope for paginated list responses.

    An object rather than a bare array so it can gain fields later
    (has_next, cursor, ...) without breaking existing clients.
    """

    items: list[T]
    total: int
    skip: int
    limit: int
