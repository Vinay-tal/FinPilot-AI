import uuid
from typing import List, Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin, utc_now

if TYPE_CHECKING:
    from app.models.user import User

class ChatConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Chat conversation session between user and AI Copilot."""
    __tablename__ = "chat_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    title: Mapped[str] = mapped_column(
        sa.String(200),
        nullable=False,
        default="Financial Copilot Discussion",
        doc="Session title or first question snippet",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="conversations")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage", back_populates="conversation", cascade="all, delete-orphan", order_by="ChatMessage.created_at"
    )

class ChatMessage(Base, UUIDPrimaryKeyMixin):
    """Individual chat turn within a copilot conversation."""
    __tablename__ = "chat_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Parent conversation ID",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="User ID reference for tenant isolation",
    )
    role: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        doc="Turn speaker: USER, ASSISTANT, SYSTEM",
    )
    content: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Message content body",
    )
    provider_used: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="mock",
        doc="Model provider: groq-llama-3.3-70b, mock, etc.",
    )
    citations_json: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="JSON citations of user data referenced in response",
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="Message timestamp",
    )

    # Relationships
    conversation: Mapped["ChatConversation"] = relationship("ChatConversation", back_populates="messages")
