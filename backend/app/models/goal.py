import uuid
from datetime import date
from typing import TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class SavingsGoal(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Savings goal milestone and progress tracking."""
    __tablename__ = "goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    name: Mapped[str] = mapped_column(
        sa.String(150),
        nullable=False,
        doc="Goal title (e.g. 6-Month Emergency Fund, Goa Vacation)",
    )
    target_amount_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="Total target amount in integer paise",
    )
    current_amount_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        default=0,
        doc="Currently accumulated amount in integer paise",
    )
    target_date: Mapped[date] = mapped_column(
        sa.Date,
        nullable=False,
        doc="Target completion date",
    )
    monthly_contribution_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        default=0,
        doc="Committed or simulated monthly contribution in paise",
    )
    category: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="SAVINGS",
        doc="Goal type: EMERGENCY_FUND, VACATION, PURCHASE, INVESTMENT, OTHER",
    )
    priority: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="MEDIUM",
        doc="Priority: HIGH, MEDIUM, LOW",
    )
    status: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="IN_PROGRESS",
        doc="Status: IN_PROGRESS, COMPLETED, PAUSED",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="goals")

    __table_args__ = (
        sa.Index("idx_goals_user_status", "user_id", "status"),
    )
