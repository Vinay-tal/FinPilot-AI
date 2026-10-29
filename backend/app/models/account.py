import uuid
from typing import List, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.transaction import Transaction

class FinancialAccount(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Financial account model (Savings, Credit Card, Investment, Cash Wallet)."""
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner reference",
    )
    name: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        doc="Account display name (e.g. HDFC Salary Account)",
    )
    account_type: Mapped[str] = mapped_column(
        sa.String(30),
        nullable=False,
        default="SAVINGS",
        doc="Type: SAVINGS, CURRENT, CREDIT_CARD, INVESTMENT, WALLET",
    )
    institution: Mapped[str] = mapped_column(
        sa.String(100),
        nullable=False,
        doc="Financial institution (e.g. HDFC Bank, SBI, Zerodha)",
    )
    account_number_mask: Mapped[str] = mapped_column(
        sa.String(20),
        nullable=True,
        doc="Masked account or card number (e.g. *4821)",
    )
    balance_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        default=0,
        doc="Current balance in integer paise (1 INR = 100 paise)",
    )
    currency: Mapped[str] = mapped_column(
        sa.String(10),
        nullable=False,
        default="INR",
        doc="Currency code",
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc="Active status of account",
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="account", cascade="all, delete-orphan"
    )
