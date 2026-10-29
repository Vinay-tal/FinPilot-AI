import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import TransactionCategory

class RecurringTransaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detected and tracked recurring bills, subscriptions, salary, and investments."""
    __tablename__ = "recurring_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Category reference",
    )
    name: Mapped[str] = mapped_column(
        sa.String(150),
        nullable=False,
        doc="Display name (e.g. Landlord Rent, Netflix, Salary)",
    )
    merchant_name: Mapped[str] = mapped_column(
        sa.String(150),
        nullable=False,
        doc="Counterparty identifier or merchant keyword",
    )
    expected_amount_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="Expected billing amount in integer paise",
    )
    frequency: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="MONTHLY",
        doc="Cadence: DAILY, WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, YEARLY",
    )
    last_detected_date: Mapped[Optional[date]] = mapped_column(
        sa.Date,
        nullable=True,
        doc="Most recent observed transaction date",
    )
    next_expected_date: Mapped[date] = mapped_column(
        sa.Date,
        nullable=False,
        index=True,
        doc="Next projected billing date",
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc="Tracking status",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="recurring_transactions")
    category: Mapped["TransactionCategory"] = relationship("TransactionCategory", back_populates="recurring_transactions")
