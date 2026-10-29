import uuid
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class FinancialInsight(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Personalized financial insights, anomaly alerts, and recommendations."""
    __tablename__ = "financial_insights"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    insight_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        doc="Type: ANOMALY, SPENDING_SPIKE, BUDGET_ALERT, SAVINGS_TIP, SHORTFALL_WARNING",
    )
    severity: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="INFO",
        doc="Severity: INFO, WARNING, CRITICAL",
    )
    title: Mapped[str] = mapped_column(
        sa.String(200),
        nullable=False,
        doc="Concise summary header",
    )
    description: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Detailed explanation and recommended action",
    )
    metadata_json: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="JSON serialized context (e.g. amount, category, confidence)",
    )
    is_read: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether user has viewed this insight",
    )
    is_resolved: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether user has taken action / dismissed this insight",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="insights")

    __table_args__ = (
        sa.Index("idx_insights_user_status", "user_id", "is_resolved"),
    )
