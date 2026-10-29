import uuid
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class Recommendation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Personalized, actionable financial recommendation with impact metrics."""
    __tablename__ = "recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    recommendation_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        index=True,
        doc="Type: BUDGET_OVERSPEND, RECURRING_REVIEW, EMERGENCY_RESERVE, GOAL_ADJUSTMENT, UPCOMING_BILL, DISCRETIONARY_SAVINGS",
    )
    title: Mapped[str] = mapped_column(
        sa.String(200),
        nullable=False,
        doc="Concise recommendation headline",
    )
    explanation: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Detailed context explaining why this recommendation was triggered",
    )
    data_period: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        doc="Relevant analytical timeframe (e.g., 'Oct 2026', 'Last 60 Days')",
    )
    estimated_impact_inr: Mapped[float] = mapped_column(
        sa.Float,
        nullable=False,
        default=0.0,
        doc="Estimated monthly or annual financial benefit in INR",
    )
    impact_assumptions: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="Underlying mathematical assumptions and calculations",
    )
    confidence: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="HIGH",
        doc="Confidence / Evidence quality: HIGH, MEDIUM, LOW",
    )
    suggested_action: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Concrete recommended step for the user",
    )
    action_type: Mapped[Optional[str]] = mapped_column(
        sa.String(50),
        nullable=True,
        doc="Action identifier: UPDATE_BUDGET, CANCEL_SUBSCRIPTION, ADJUST_GOAL, DISMISS",
    )
    action_payload_json: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="JSON serialized payload to execute this action programmatically",
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="new",
        index=True,
        doc="Lifecycle state: new, accepted, dismissed, completed",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recommendations")

    __table_args__ = (
        sa.Index("idx_recommendations_user_status", "user_id", "status"),
    )
