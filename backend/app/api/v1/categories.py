from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.category import CategoryCreate, CategoryResponse
from app.services.category_service import list_categories, create_category

router = APIRouter(prefix="/categories", tags=["Categories"])

@router.get("", response_model=List[CategoryResponse])
def get_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CategoryResponse]:
    """Retrieve all available system and user-specific categories."""
    categories = list_categories(db, current_user.id)
    return [CategoryResponse.model_validate(c) for c in categories]

@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def add_category(
    cat_in: CategoryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CategoryResponse:
    """Create a new custom category for the user."""
    cat = create_category(db, current_user.id, cat_in)
    return CategoryResponse.model_validate(cat)
