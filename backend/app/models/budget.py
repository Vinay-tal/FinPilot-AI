import uuid
from typing import TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.category import TransactionCategory

class Budget(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Category budget allocations and spending limits per month."""
    __tablename__ = "budgets"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Target category ID",
    )
    month: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        doc="Budget month (1-12)",
    )
    year: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        doc="Budget year (e.g. 2026)",
    )
    amount_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="Monthly spending limit in integer paise",
    )
    alert_threshold: Mapped[float] = mapped_column(
        sa.Numeric(4, 2),
        nullable=False,
        default=0.80,
        doc="Pacing alert percentage trigger (e.g. 0.80 for 80%)",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="budgets")
    category: Mapped["TransactionCategory"] = relationship("TransactionCategory", back_populates="budgets")

    __table_args__ = (
        sa.UniqueConstraint("user_id", "category_id", "month", "year", name="uq_user_category_month_year"),
        sa.Index("idx_budgets_user_period", "user_id", "year", "month"),
    )
