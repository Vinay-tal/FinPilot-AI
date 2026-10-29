import uuid
from typing import List, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import FinancialAccount
    from app.models.transaction import Transaction
    from app.models.budget import Budget
    from app.models.goal import SavingsGoal
    from app.models.recurring_transaction import RecurringTransaction
    from app.models.financial_insight import FinancialInsight
    from app.models.notification import UserNotification
    from app.models.chat import ChatConversation
    from app.models.saved_scenario import SavedScenario
    from app.models.recommendation import Recommendation

class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """User account model storing identity and authentication credentials."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique user email address",
    )
    password_hash: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Bcrypt hashed password",
    )
    full_name: Mapped[str] = mapped_column(
        sa.String(150),
        nullable=False,
        doc="Full display name",
    )
    currency: Mapped[str] = mapped_column(
        sa.String(10),
        nullable=False,
        default="INR",
        doc="Currency code (default: INR)",
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        doc="Whether the user is currently active",
    )
    is_demo: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="Flag identifying synthetic demo account",
    )

    # Relationships
    accounts: Mapped[List["FinancialAccount"]] = relationship(
        "FinancialAccount", back_populates="user", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="user", cascade="all, delete-orphan"
    )
    budgets: Mapped[List["Budget"]] = relationship(
        "Budget", back_populates="user", cascade="all, delete-orphan"
    )
    goals: Mapped[List["SavingsGoal"]] = relationship(
        "SavingsGoal", back_populates="user", cascade="all, delete-orphan"
    )
    recurring_transactions: Mapped[List["RecurringTransaction"]] = relationship(
        "RecurringTransaction", back_populates="user", cascade="all, delete-orphan"
    )
    insights: Mapped[List["FinancialInsight"]] = relationship(
        "FinancialInsight", back_populates="user", cascade="all, delete-orphan"
    )
    notifications: Mapped[List["UserNotification"]] = relationship(
        "UserNotification", back_populates="user", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["ChatConversation"]] = relationship(
        "ChatConversation", back_populates="user", cascade="all, delete-orphan"
    )
    saved_scenarios: Mapped[List["SavedScenario"]] = relationship(
        "SavedScenario", back_populates="user", cascade="all, delete-orphan"
    )
    recommendations: Mapped[List["Recommendation"]] = relationship(
        "Recommendation", back_populates="user", cascade="all, delete-orphan"
    )
