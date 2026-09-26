import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base
from app.db.models.mixins import TimestampMixin


class RefreshToken(TimestampMixin, Base):
    """A persisted, revocable refresh token.

    Only the SHA-256 hash is stored. A leaked database therefore does not
    hand an attacker usable sessions -- the same reasoning as password
    hashing, applied to long-lived tokens.

    ``family_id`` groups every token descended from one login. Rotation
    issues a new token and revokes the old one; if a REVOKED token is ever
    presented again, it was stolen, and the whole family is revoked at once.
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )

    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False, index=True)

    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"<RefreshToken user={self.user_id} revoked={self.revoked_at is not None}>"
