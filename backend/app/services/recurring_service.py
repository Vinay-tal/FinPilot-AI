import uuid
from typing import List
from sqlalchemy.orm import Session, joinedload
from app.models.recurring_transaction import RecurringTransaction
from app.schemas.recurring import RecurringCreate, RecurringResponse
from app.core.exceptions import NotFoundException, ForbiddenException

def list_recurring(db: Session, user_id: uuid.UUID) -> List[RecurringResponse]:
    """Retrieve recurring obligations for user."""
    items = db.query(RecurringTransaction).options(
        joinedload(RecurringTransaction.category)
    ).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
    ).order_by(RecurringTransaction.next_expected_date.asc()).all()

    results = []
    for r in items:
        res = RecurringResponse.model_validate(r)
        if r.category:
            res.category_name = r.category.name
            res.category_color = r.category.color
        results.append(res)
    return results

def create_recurring(db: Session, user_id: uuid.UUID, r_in: RecurringCreate) -> RecurringResponse:
    """Create a new recurring subscription or bill."""
    recurring = RecurringTransaction(
        user_id=user_id,
        category_id=r_in.category_id,
        name=r_in.name,
        merchant_name=r_in.merchant_name,
        expected_amount_paise=r_in.expected_amount_paise,
        frequency=r_in.frequency.upper(),
        next_expected_date=r_in.next_expected_date,
        is_active=True,
    )
    db.add(recurring)
    db.flush()
    return RecurringResponse.model_validate(recurring)

def delete_recurring(db: Session, user_id: uuid.UUID, r_id: uuid.UUID) -> None:
    """Delete a recurring tracking rule."""
    r = db.query(RecurringTransaction).filter(RecurringTransaction.id == r_id).first()
    if not r:
        raise NotFoundException("RecurringTransaction", r_id)
    if r.user_id != user_id:
        raise ForbiddenException("You cannot delete another user's recurring obligation.")
    db.delete(r)
    db.flush()
