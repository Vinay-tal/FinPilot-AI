import uuid
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class SavedScenario(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Named financial 'What-If' scenarios saved by user."""
    __tablename__ = "saved_scenarios"

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
        doc="Human-readable scenario title (e.g., '15% Salary Hike + Car EMI')",
    )
    description: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="User notes or context for this simulation",
    )
    params_json: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="JSON serialized simulation parameters",
    )
    results_summary_json: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="JSON serialized summary results (monthly diff, annual impact, breach months)",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="saved_scenarios")

    __table_args__ = (
        sa.Index("idx_scenarios_user_created", "user_id", "created_at"),
    )
