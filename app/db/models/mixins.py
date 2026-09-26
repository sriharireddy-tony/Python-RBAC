from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Database-managed created_at / updated_at columns.

    The values come from the database clock (``now()``), not from Python, so
    they are correct even for rows inserted outside the ORM.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class SoftDeleteMixin:
    """Marks rows as deleted instead of removing them.

    RBAC systems need history: "who approved this in March" must still
    resolve after that person leaves. Every query on a soft-deletable model
    must filter ``deleted_at IS NULL`` — applied by the ``_active()`` helper
    at the top of each repository rather than at each call site.
    """

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        default=None,
        nullable=True,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
