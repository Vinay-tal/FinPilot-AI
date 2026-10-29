import uuid
from datetime import datetime
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDPrimaryKeyMixin, utc_now

class ModelEvaluation(Base, UUIDPrimaryKeyMixin):
    """Stores ML experiment evaluation metrics, confusion matrices, and audit logs."""
    __tablename__ = "model_evaluations"

    model_name: Mapped[str] = mapped_column(
        sa.String(80),
        nullable=False,
        index=True,
        doc="Name of model evaluated: transaction_classifier, cashflow_forecaster, anomaly_detector",
    )
    version: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        doc="Model version string",
    )
    evaluation_type: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="TEST_SPLIT",
        doc="Evaluation method: STRATIFIED_CV, TEST_SPLIT, BACKTEST",
    )
    metrics_json: Mapped[str] = mapped_column(
        sa.Text,
        nullable=False,
        doc="JSON serialized performance metrics (Accuracy, F1, Precision, Recall, RMSE, MAE)",
    )
    sample_size: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        doc="Number of records evaluated",
    )
    evaluated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="Timestamp of evaluation",
    )
