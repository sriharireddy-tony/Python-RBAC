import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.models.associations import role_permissions, user_roles
from app.db.models.mixins import SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from app.db.models.permission import Permission
    from app.db.models.user import User


class Role(TimestampMixin, SoftDeleteMixin, Base):
    """A tenant-defined grouping of permissions.

    Tenant-scoped on purpose: Acme and ABC Corp must both be able to have a
    role called "Admin", and each customer decides what their roles mean.
    Compare with Permission, which is global.
    """

    __tablename__ = "roles"

    __table_args__ = (
        Index(
            "uq_roles_tenant_name_active",
            "tenant_id",
            "name",
            unique=True,
            postgresql_where="deleted_at IS NULL",
        ),
        UniqueConstraint("tenant_id", "id", name="uq_roles_tenant_id_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # System roles (e.g. the Admin created at registration) are protected
    # from deletion, so a tenant cannot lock itself out of its own account.
    is_system_role: Mapped[bool] = mapped_column(
        Boolean, server_default="false", nullable=False
    )

    users: Mapped[list["User"]] = relationship(
        secondary=user_roles,
        back_populates="roles",
    )

    permissions: Mapped[list["Permission"]] = relationship(
        secondary=role_permissions,
        back_populates="roles",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r} tenant={self.tenant_id}>"
