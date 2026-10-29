import uuid
from typing import List
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.models.category import TransactionCategory
from app.schemas.category import CategoryCreate
from app.core.exceptions import ConflictException

def list_categories(db: Session, user_id: uuid.UUID) -> List[TransactionCategory]:
    """Retrieve all available system categories and user-specific custom categories."""
    return db.query(TransactionCategory).filter(
        sa.or_(
            TransactionCategory.is_system == True,
            TransactionCategory.user_id == user_id,
        )
    ).order_by(TransactionCategory.is_income.asc(), TransactionCategory.name.asc()).all()

def create_category(db: Session, user_id: uuid.UUID, cat_in: CategoryCreate) -> TransactionCategory:
    """Create a new custom category for the user."""
    # Check if a category with same slug already exists for this user or as system
    existing = db.query(TransactionCategory).filter(
        TransactionCategory.slug == cat_in.slug.lower(),
        sa.or_(TransactionCategory.is_system == True, TransactionCategory.user_id == user_id),
    ).first()
    if existing:
        raise ConflictException(f"Category with slug '{cat_in.slug}' already exists.")

    category = TransactionCategory(
        user_id=user_id,
        name=cat_in.name,
        slug=cat_in.slug.lower(),
        icon=cat_in.icon,
        color=cat_in.color,
        is_income=cat_in.is_income,
        is_system=False,
    )
    db.add(category)
    db.flush()
    return category
