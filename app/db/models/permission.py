import uuid
from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.db.models.associations import role_permissions
from app.db.models.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.role import Role


class Permission(TimestampMixin, Base):
    """A single action the software can perform, e.g. users:delete.

    Deliberately has NO tenant_id: permissions describe what this codebase
    can do, which is identical for every customer. They are seeded by a data
    migration and are not user-editable -- adding one means shipping code
    that checks it.
    """

    __tablename__ = "permissions"

    __table_args__ = (
        UniqueConstraint("resource", "action", name="uq_permissions_resource_action"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    roles: Mapped[list["Role"]] = relationship(
        secondary=role_permissions,
        back_populates="permissions",
    )

    @property
    def code(self) -> str:
        """The form used everywhere else in the app: "users:delete"."""
        return f"{self.resource}:{self.action}"

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"
