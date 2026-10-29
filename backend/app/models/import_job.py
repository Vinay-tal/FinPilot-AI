import uuid
from datetime import datetime
from typing import Optional, TYPE_CHECKING
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

class ImportJob(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Audit log and status tracker for CSV statement import operations."""
    __tablename__ = "import_jobs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Uploader user ID",
    )
    filename: Mapped[str] = mapped_column(
        sa.String(255),
        nullable=False,
        doc="Original uploaded file name",
    )
    bank_format: Mapped[str] = mapped_column(
        sa.String(50),
        nullable=False,
        default="GENERIC",
        doc="Bank parser profile: HDFC, SBI, ICICI, AXIS, KOTAK, GENERIC",
    )
    status: Mapped[str] = mapped_column(
        sa.String(30),
        nullable=False,
        default="PENDING",
        doc="Status: PENDING, PROCESSING, COMPLETED, FAILED",
    )
    total_rows: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        doc="Total rows parsed from statement",
    )
    imported_rows: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        doc="Successfully inserted transaction count",
    )
    duplicate_rows: Mapped[int] = mapped_column(
        sa.Integer,
        nullable=False,
        default=0,
        doc="Deduplicated/skipped row count",
    )
    error_log: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Error diagnostic log if parsing failed",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="Timestamp of completion",
    )
