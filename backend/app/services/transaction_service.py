import uuid
import hashlib
from datetime import date
from typing import Optional, List, Tuple
import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload
from app.models.transaction import Transaction
from app.models.account import FinancialAccount
from app.models.category import TransactionCategory
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionResponse
from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException

def compute_fingerprint(user_id: uuid.UUID, tx_date: date, amount_paise: int, tx_type: str, narration: str) -> str:
    """Compute SHA-256 fingerprint for deduplication."""
    clean_narration = " ".join(narration.strip().lower().split())
    payload = f"{user_id}|{tx_date.isoformat()}|{amount_paise}|{tx_type.upper()}|{clean_narration}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def create_transaction(
    db: Session,
    user_id: uuid.UUID,
    tx_in: TransactionCreate,
    categorization_method: str = "MANUAL",
    categorization_confidence: Optional[float] = 1.0,
    allow_duplicate: bool = False,
) -> Transaction:
    """Create a new transaction with balance adjustment and deduplication."""
    # 1. Verify account belongs to user
    account = db.query(FinancialAccount).filter(FinancialAccount.id == tx_in.account_id).first()
    if not account:
        raise NotFoundException("FinancialAccount", tx_in.account_id)
    if account.user_id != user_id:
        raise ForbiddenException("Account does not belong to the authenticated user.")

    # 2. Verify category exists
    category = db.query(TransactionCategory).filter(TransactionCategory.id == tx_in.category_id).first()
    if not category:
        raise NotFoundException("TransactionCategory", tx_in.category_id)

    # 3. Calculate fingerprint and deduplicate
    fingerprint = compute_fingerprint(
        user_id=user_id,
        tx_date=tx_in.date,
        amount_paise=tx_in.amount_paise,
        tx_type=tx_in.transaction_type,
        narration=tx_in.narration,
    )
    if not allow_duplicate:
        dup = db.query(Transaction).filter(
            Transaction.user_id == user_id,
            Transaction.fingerprint == fingerprint,
        ).first()
        if dup:
            raise ConflictException(
                "A transaction with identical date, amount, type, and narration already exists.",
                details={"existing_transaction_id": str(dup.id)}
            )

    # 4. Create transaction
    tx = Transaction(
        user_id=user_id,
        account_id=tx_in.account_id,
        category_id=tx_in.category_id,
        date=tx_in.date,
        amount_paise=tx_in.amount_paise,
        transaction_type=tx_in.transaction_type.upper(),
        narration=tx_in.narration,
        raw_narration=tx_in.raw_narration or tx_in.narration,
        merchant_name=tx_in.merchant_name,
        payment_mode=tx_in.payment_mode.upper(),
        reference_id=tx_in.reference_id,
        fingerprint=fingerprint,
        categorization_method=categorization_method,
        categorization_confidence=categorization_confidence,
    )
    db.add(tx)

    # 5. Update account balance
    if tx.transaction_type == "CREDIT":
        account.balance_paise += tx.amount_paise
    else:
        account.balance_paise -= tx.amount_paise

    db.flush()
    return tx

def list_transactions(
    db: Session,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 20,
    account_id: Optional[uuid.UUID] = None,
    category_id: Optional[uuid.UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    tx_type: Optional[str] = None,
    payment_mode: Optional[str] = None,
    search: Optional[str] = None,
    min_amount_paise: Optional[int] = None,
    max_amount_paise: Optional[int] = None,
    sort_by: str = "date",
    sort_order: str = "desc",
) -> Tuple[List[TransactionResponse], int]:
    """Search and paginate transactions with user isolation."""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)

    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if tx_type:
        query = query.filter(Transaction.transaction_type == tx_type.upper())
    if payment_mode:
        query = query.filter(Transaction.payment_mode == payment_mode.upper())
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            sa.or_(
                Transaction.narration.ilike(search_filter),
                Transaction.merchant_name.ilike(search_filter),
                Transaction.reference_id.ilike(search_filter),
            )
        )
    if min_amount_paise is not None:
        query = query.filter(Transaction.amount_paise >= min_amount_paise)
    if max_amount_paise is not None:
        query = query.filter(Transaction.amount_paise <= max_amount_paise)

    total = query.count()

    # Sorting
    sort_column = getattr(Transaction, sort_by, Transaction.date)
    if sort_order.lower() == "asc":
        query = query.order_by(sort_column.asc(), Transaction.created_at.asc())
    else:
        query = query.order_by(sort_column.desc(), Transaction.created_at.desc())

    offset = (page - 1) * limit
    transactions = query.options(
        joinedload(Transaction.category),
        joinedload(Transaction.account),
    ).offset(offset).limit(limit).all()

    # Hydrate response models
    items = []
    for tx in transactions:
        item = TransactionResponse.model_validate(tx)
        if tx.category:
            item.category_name = tx.category.name
            item.category_color = tx.category.color
        if tx.account:
            item.account_name = tx.account.name
        items.append(item)

    return items, total

def get_transaction(db: Session, user_id: uuid.UUID, tx_id: uuid.UUID) -> TransactionResponse:
    """Retrieve single transaction with user verification."""
    tx = db.query(Transaction).options(
        joinedload(Transaction.category),
        joinedload(Transaction.account),
    ).filter(Transaction.id == tx_id).first()
    if not tx:
        raise NotFoundException("Transaction", tx_id)
    if tx.user_id != user_id:
        raise ForbiddenException("You do not have permission to view this transaction.")

    res = TransactionResponse.model_validate(tx)
    if tx.category:
        res.category_name = tx.category.name
        res.category_color = tx.category.color
    if tx.account:
        res.account_name = tx.account.name
    return res

def delete_transaction(db: Session, user_id: uuid.UUID, tx_id: uuid.UUID) -> None:
    """Delete a transaction and reverse its balance impact on account."""
    tx = db.query(Transaction).filter(Transaction.id == tx_id).first()
    if not tx:
        raise NotFoundException("Transaction", tx_id)
    if tx.user_id != user_id:
        raise ForbiddenException("You cannot delete another user's transaction.")

    account = db.query(FinancialAccount).filter(FinancialAccount.id == tx.account_id).first()
    if account:
        if tx.transaction_type == "CREDIT":
            account.balance_paise -= tx.amount_paise
        else:
            account.balance_paise += tx.amount_paise

    db.delete(tx)
    db.flush()
