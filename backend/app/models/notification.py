import uuid
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class UserNotification(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User in-app alert and notification messages."""
    __tablename__ = "user_notifications"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Recipient user ID",
    )
    title: Mapped[str] = mapped_column(
        sa.String(150),
        nullable=False,
        doc="Notification headline",
    )
    message: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Notification description text",
    )
    notification_type: Mapped[str] = mapped_column(
        sa.String(30),
        nullable=False,
        default="ALERT",
        doc="Type: ALERT, REMINDER, SYSTEM, TIP",
    )
    is_read: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        index=True,
        doc="Read/unread flag",
    )
    action_url: Mapped[Optional[str]] = mapped_column(
        sa.String(255),
        nullable=True,
        doc="Optional deep-link URL in UI",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="notifications")
