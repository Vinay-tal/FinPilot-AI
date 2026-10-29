import uuid
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.transaction import TransactionCreate, TransactionResponse
from app.schemas.common import PaginatedResponse
from app.services.transaction_service import (
    create_transaction,
    list_transactions,
    get_transaction,
    delete_transaction,
)

router = APIRouter(prefix="/transactions", tags=["Transactions Ledger"])

@router.get("", response_model=PaginatedResponse[TransactionResponse])
def get_transactions(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    account_id: Optional[uuid.UUID] = Query(default=None),
    category_id: Optional[uuid.UUID] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    tx_type: Optional[str] = Query(default=None, alias="type", description="DEBIT or CREDIT"),
    payment_mode: Optional[str] = Query(default=None),
    search: Optional[str] = Query(default=None, description="Search in narration, merchant, ref"),
    min_amount_paise: Optional[int] = Query(default=None, ge=0),
    max_amount_paise: Optional[int] = Query(default=None, ge=0),
    sort_by: str = Query(default="date", description="date, amount_paise, created_at"),
    sort_order: str = Query(default="desc", description="asc or desc"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PaginatedResponse[TransactionResponse]:
    """Retrieve filtered, sorted, and paginated transaction ledger records."""
    items, total = list_transactions(
        db=db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        account_id=account_id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        tx_type=tx_type,
        payment_mode=payment_mode,
        search=search,
        min_amount_paise=min_amount_paise,
        max_amount_paise=max_amount_paise,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    total_pages = (total + limit - 1) // limit if total > 0 else 1

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        total_pages=total_pages,
    )

@router.post("", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
def add_transaction(
    tx_in: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """Create a new transaction with automatic balance updating and deduplication."""
    tx = create_transaction(db, current_user.id, tx_in)
    return get_transaction(db, current_user.id, tx.id)

@router.get("/{tx_id}", response_model=TransactionResponse)
def get_single_transaction(
    tx_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """Retrieve single transaction details."""
    return get_transaction(db, current_user.id, tx_id)

@router.delete("/{tx_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_transaction(
    tx_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a transaction and adjust account balance."""
    delete_transaction(db, current_user.id, tx_id)

from pydantic import BaseModel
class TransactionReclassify(BaseModel):
    category_id: uuid.UUID

@router.patch("/{tx_id}/reclassify", response_model=TransactionResponse)
def reclassify_transaction(
    tx_id: uuid.UUID,
    body: TransactionReclassify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """User correction feedback loop: updates category and marks categorization_method='MANUAL'."""
    from app.services.categorization_service import record_user_correction
    record_user_correction(
        db=db,
        transaction_id=str(tx_id),
        new_category_id=str(body.category_id),
        user_id=str(current_user.id),
    )
    return get_transaction(db, current_user.id, tx_id)

