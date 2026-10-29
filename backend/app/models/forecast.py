import uuid
from datetime import date
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User

class Forecast(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Persisted cash flow projections and uncertainty intervals."""
    __tablename__ = "forecasts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Owner user ID",
    )
    account_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
        doc="Specific account ID or NULL for aggregated user balance",
    )
    forecast_date: Mapped[date] = mapped_column(
        sa.Date,
        nullable=False,
        index=True,
        doc="Target projected date",
    )
    horizon_days: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=30,
        doc="Projection horizon: 30, 60, 90 days",
    )
    predicted_balance_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="Expected balance in integer paise",
    )
    lower_bound_80_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="80% confidence interval lower bound in integer paise",
    )
    upper_bound_80_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="80% confidence interval upper bound in integer paise",
    )
    lower_bound_95_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="95% confidence interval lower bound in integer paise",
    )
    upper_bound_95_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        doc="95% confidence interval upper bound in integer paise",
    )
    projected_net_change_paise: Mapped[int] = mapped_column(
        sa.BigInteger,
        nullable=False,
        default=0,
        doc="Projected daily net cash flow change in integer paise",
    )
    shortfall_flag: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        doc="True if balance breaches minimum buffer threshold",
    )
    model_version: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="holt_winters_v1",
        doc="Identifier of model algorithm used",
    )

    __table_args__ = (
        sa.Index("idx_forecasts_user_date", "user_id", "forecast_date"),
    )
