import uuid
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.models.associations import user_roles
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.role import Role


class UserStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class User(TimestampMixin, SoftDeleteMixin, Base):
    __tablename__ = "users"

    __table_args__ = (
        # Email is unique PER TENANT, not globally: the same person may hold
        # an account at two different customers. This is why login needs a
        # tenant_slug -- email alone does not identify a user.
        #
        # A partial index so a soft-deleted user's address can be reused.
        Index(
            "uq_users_tenant_email_active",
            "tenant_id",
            "email",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
        # Target for the composite foreign key on user_roles. Postgres requires
        # the referenced columns to be uniquely constrained.
        UniqueConstraint("tenant_id", "id", name="uq_users_tenant_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    email: Mapped[str] = mapped_column(String(255), nullable=False)

    # Never the password itself, and never exposed on any *Read schema.
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    first_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    status: Mapped[UserStatus] = mapped_column(
        SQLEnum(
            UserStatus,
            name="user_status",
            values_callable=lambda enum_cls: [m.value for m in enum_cls],
        ),
        server_default=UserStatus.ACTIVE.value,
        nullable=False,
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    roles: Mapped[list["Role"]] = relationship(
        secondary=user_roles,
        back_populates="users",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} tenant={self.tenant_id}>"
