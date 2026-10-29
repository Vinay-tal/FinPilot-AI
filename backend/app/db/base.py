from datetime import datetime, timezone
import uuid
from typing import Any
import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

def utc_now() -> datetime:
    """Return timezone-aware current UTC datetime."""
    return datetime.now(timezone.utc)

class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy 2.0 models."""
    pass

class UUIDPrimaryKeyMixin:
    """Mixin adding standard UUID primary key."""
    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        doc="Unique UUID primary key",
    )

class TimestampMixin:
    """Mixin adding consistent UTC created_at and updated_at timestamps."""
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utc_now,
        nullable=False,
        doc="UTC record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
        doc="UTC record last updated timestamp",
    )
