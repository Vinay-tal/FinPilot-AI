import uuid
from typing import List, Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.transaction import Transaction
    from app.models.budget import Budget
    from app.models.recurring_transaction import RecurringTransaction

class TransactionCategory(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Category classification model for income and expenses."""
    __tablename__ = "categories"

    name: Mapped[str] = mapped_column(
        sa.String(80),
        nullable=False,
        doc="Display name (e.g. Food & Dining)",
    )
    slug: Mapped[str] = mapped_column(
        sa.String(80),
        nullable=False,
        index=True,
        doc="Unique slug identifier (e.g. food-dining)",
    )
    icon: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="tag",
        doc="Lucide icon identifier",
    )
    color: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="#64748b",
        doc="Hex color code",
    )
    is_income: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="True if income category, False if expense",
    )
    is_system: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc="True if default system category, False if user custom",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Owner user ID if custom category, NULL if system-wide",
    )

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="category"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="category"
    )
    recurring_transactions: Mapped[List["RecurringTransaction"]] = relationship(
        "RecurringTransaction", back_populates="category"
    )
