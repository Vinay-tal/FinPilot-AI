import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.account import AccountCreate, AccountUpdate, AccountResponse
from app.services.account_service import list_accounts, get_account, create_account, update_account, delete_account

router = APIRouter(prefix="/accounts", tags=["Financial Accounts"])

@router.get("", response_model=List[AccountResponse])
def get_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[AccountResponse]:
    """List all accounts belonging strictly to the authenticated user."""
    accounts = list_accounts(db, current_user.id)
    return [AccountResponse.model_validate(a) for a in accounts]

@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
def add_account(
    account_in: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Create a new financial account for the authenticated user."""
    account = create_account(db, current_user.id, account_in)
    return AccountResponse.model_validate(account)

@router.get("/{account_id}", response_model=AccountResponse)
def get_single_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Retrieve single account details with tenant isolation."""
    account = get_account(db, current_user.id, account_id)
    return AccountResponse.model_validate(account)

@router.put("/{account_id}", response_model=AccountResponse)
def modify_account(
    account_id: uuid.UUID,
    account_in: AccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AccountResponse:
    """Update account details."""
    account = update_account(db, current_user.id, account_id, account_in)
    return AccountResponse.model_validate(account)

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_account(
    account_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Deactivate or remove account."""
    delete_account(db, current_user.id, account_id)
