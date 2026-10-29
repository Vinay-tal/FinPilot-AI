import uuid
from typing import List
from sqlalchemy.orm import Session
from app.models.account import FinancialAccount
from app.schemas.account import AccountCreate, AccountUpdate
from app.core.exceptions import NotFoundException, ForbiddenException

def list_accounts(db: Session, user_id: uuid.UUID) -> List[FinancialAccount]:
    """Retrieve all accounts belonging strictly to the authenticated user."""
    return db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
    ).order_by(FinancialAccount.name.asc()).all()

def get_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> FinancialAccount:
    """Retrieve a single account with user tenant verification."""
    account = db.query(FinancialAccount).filter(FinancialAccount.id == account_id).first()
    if not account:
        raise NotFoundException("FinancialAccount", account_id)
    if account.user_id != user_id:
        raise ForbiddenException("You cannot access another user's financial account.")
    return account

def create_account(db: Session, user_id: uuid.UUID, account_in: AccountCreate) -> FinancialAccount:
    """Create a new financial account for the user."""
    account = FinancialAccount(
        user_id=user_id,
        name=account_in.name,
        account_type=account_in.account_type.upper(),
        institution=account_in.institution,
        account_number_mask=account_in.account_number_mask,
        balance_paise=account_in.balance_paise,
        currency=account_in.currency or "INR",
        is_active=True,
    )
    db.add(account)
    db.flush()
    return account

def update_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID, account_in: AccountUpdate) -> FinancialAccount:
    """Update account details with user isolation."""
    account = get_account(db, user_id, account_id)
    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "account_type" and value:
            setattr(account, field, value.upper())
        else:
            setattr(account, field, value)
    db.flush()
    return account

def delete_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
    """Deactivate or delete an account."""
    account = get_account(db, user_id, account_id)
    account.is_active = False
    db.flush()
