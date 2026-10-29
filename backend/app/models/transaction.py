import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.account import FinancialAccount
    from app.models.category import TransactionCategory

class Transaction(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Core transaction ledger storing all income, expense, and transfer movements."""
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Tenant user ID reference",
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Linked financial account ID",
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Assigned category ID",
    )
    date: Mapped[date] = mapped_column(
        sa.Date,
        nullable=False,
        index=True,
        doc="Posting date of the transaction",
    )
    amount_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="Transaction amount in integer paise (strictly >= 0)",
    )
    transaction_type: Mapped[str] = mapped_column(
        sa.String(10),
        nullable=False,
        doc="Movement direction: DEBIT or CREDIT",
    )
    narration: Mapped[str] = mapped_column(
        sa.String(500),
        nullable=False,
        doc="Cleaned description / narration text",
    )
    raw_narration: Mapped[Optional[str]] = mapped_column(
        sa.String(1000),
        nullable=True,
        doc="Original raw bank statement line or SMS text",
    )
    merchant_name: Mapped[Optional[str]] = mapped_column(
        sa.String(150),
        nullable=True,
        index=True,
        doc="Extracted merchant or counterparty name (e.g. Swiggy, BESCOM)",
    )
    payment_mode: Mapped[str] = mapped_column(
        sa.String(30),
        nullable=False,
        default="UPI",
        doc="Payment instrument: UPI, NET_BANKING, DEBIT_CARD, CREDIT_CARD, CHEQUE, CASH",
    )
    reference_id: Mapped[Optional[str]] = mapped_column(
        sa.String(100),
        nullable=True,
        index=True,
        doc="Bank UTR / UPI reference number / Cheque number",
    )
    is_recurring: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Whether this transaction was matched to a recurring subscription/bill",
    )
    fingerprint: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        index=True,
        doc="SHA-256 hash (user_id, date, amount, type, normalized narration) for deduplication",
    )
    categorization_method: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=False,
        default="MANUAL",
        doc="How category was assigned: RULE, ML, MANUAL, DEFAULT",
    )
    categorization_confidence: Mapped[Optional[float]] = mapped_column(
        sa.Numeric(4, 3),
        nullable=True,
        doc="Prediction confidence score between 0.000 and 1.000",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="transactions")
    account: Mapped["FinancialAccount"] = relationship("FinancialAccount", back_populates="transactions")
    category: Mapped["TransactionCategory"] = relationship("TransactionCategory", back_populates="transactions")

    __table_args__ = (
        sa.Index("idx_transactions_user_date", "user_id", "date"),
        sa.Index("idx_transactions_user_fingerprint", "user_id", "fingerprint"),
        sa.Index("idx_transactions_user_cat_date", "user_id", "category_id", "date"),
    )
