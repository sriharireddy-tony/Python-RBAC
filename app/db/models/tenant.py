import uuid
from enum import StrEnum

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.mixins import TimestampMixin


class TenantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    status: Mapped[TenantStatus] = mapped_column(
        SQLEnum(
            TenantStatus,
            name="tenant_status",
            # Persist the member *values* ("active"), not the member names
            # ("ACTIVE"), which is what SQLAlchemy would use by default.
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default=TenantStatus.ACTIVE.value,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Tenant id={self.id} slug={self.slug!r}>"
