import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.recurring import RecurringCreate, RecurringResponse
from app.services.recurring_service import list_recurring, create_recurring, delete_recurring

router = APIRouter(prefix="/recurring", tags=["Recurring Obligations"])

@router.get("", response_model=List[RecurringResponse])
def get_recurring_transactions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecurringResponse]:
    """Retrieve all recurring obligations for the user."""
    return list_recurring(db, current_user.id)

@router.post("", response_model=RecurringResponse, status_code=status.HTTP_201_CREATED)
def add_recurring_transaction(
    r_in: RecurringCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecurringResponse:
    """Create a recurring bill or subscription."""
    return create_recurring(db, current_user.id, r_in)

@router.delete("/{r_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_recurring_transaction(
    r_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a recurring tracking item."""
    delete_recurring(db, current_user.id, r_id)
