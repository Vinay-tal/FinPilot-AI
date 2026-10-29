import uuid
from datetime import date, timedelta
from typing import List, Optional
import sqlalchemy as sa
from sqlalchemy.orm import Session, joinedload
from app.models.budget import Budget
from app.models.transaction import Transaction
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.core.exceptions import NotFoundException, ForbiddenException, ConflictException

def list_budgets(db: Session, user_id: uuid.UUID, month: int, year: int) -> List[BudgetResponse]:
    """Retrieve all category budgets for month/year with real-time spend actuals."""
    budgets = db.query(Budget).options(
        joinedload(Budget.category)
    ).filter(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.year == year,
    ).all()

    # Pre-calculate spent amounts per category for this month
    # Using date ranges for dialect compatibility across both SQLite and PostgreSQL
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    spend_query = db.query(
        Transaction.category_id,
        sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0).label("spent")
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_date,
        Transaction.date < end_date,
    ).group_by(Transaction.category_id).all()

    spend_map = {row.category_id: int(row.spent) for row in spend_query}

    results = []
    for b in budgets:
        spent = spend_map.get(b.category_id, 0)
        remaining = max(0, b.amount_paise - spent)
        pct = round((spent / b.amount_paise) * 100.0, 1) if b.amount_paise > 0 else 0.0
        
        status = "NORMAL"
        threshold = float(b.alert_threshold or 0.80)
        if spent >= b.amount_paise:
            status = "EXCEEDED"
        elif (spent / b.amount_paise) >= threshold:
            status = "WARNING"

        res = BudgetResponse.model_validate(b)
        res.spent_paise = spent
        res.remaining_paise = remaining
        res.pacing_pct = pct
        res.alert_status = status
        if b.category:
            res.category_name = b.category.name
            res.category_color = b.category.color
        results.append(res)

    return results

def create_budget(db: Session, user_id: uuid.UUID, b_in: BudgetCreate) -> BudgetResponse:
    """Create a new monthly category budget with unique constraint check."""
    existing = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.category_id == b_in.category_id,
        Budget.month == b_in.month,
        Budget.year == b_in.year,
    ).first()
    if existing:
        raise ConflictException(
            f"A budget for this category already exists for {b_in.month}/{b_in.year}.",
            details={"budget_id": str(existing.id)}
        )

    budget = Budget(
        user_id=user_id,
        category_id=b_in.category_id,
        month=b_in.month,
        year=b_in.year,
        amount_paise=b_in.amount_paise,
        alert_threshold=b_in.alert_threshold,
    )
    db.add(budget)
    db.flush()

    res = BudgetResponse.model_validate(budget)
    res.spent_paise = 0
    res.remaining_paise = b_in.amount_paise
    res.pacing_pct = 0.0
    res.alert_status = "NORMAL"
    return res

def update_budget(db: Session, user_id: uuid.UUID, budget_id: uuid.UUID, b_in: BudgetUpdate) -> BudgetResponse:
    """Update an existing budget allocation."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise NotFoundException("Budget", budget_id)
    if budget.user_id != user_id:
        raise ForbiddenException("You cannot edit another user's budget.")

    if b_in.amount_paise is not None:
        budget.amount_paise = b_in.amount_paise
    if b_in.alert_threshold is not None:
        budget.alert_threshold = b_in.alert_threshold

    db.flush()
    res = BudgetResponse.model_validate(budget)
    return res

def delete_budget(db: Session, user_id: uuid.UUID, budget_id: uuid.UUID) -> None:
    """Delete a budget item."""
    budget = db.query(Budget).filter(Budget.id == budget_id).first()
    if not budget:
        raise NotFoundException("Budget", budget_id)
    if budget.user_id != user_id:
        raise ForbiddenException("You cannot delete another user's budget.")
    db.delete(budget)
    db.flush()

def get_budget_recommendations(db: Session, user_id: uuid.UUID, month: int, year: int):
    """
    Generate proactive category budget recommendations from historical spending.
    Essentials (Groceries, Utilities, Housing, Transport) receive historical average + 5% inflation buffer.
    Discretionary categories receive historical average - 10% optimization target.
    """
    from app.models.category import TransactionCategory
    from app.schemas.planning import BudgetRecommendationItem, BudgetRecommendationsResponse

    today = date.today()
    # 90 days lookback
    start_90d = today - timedelta(days=90)

    # Categories with spending
    cat_rows = db.query(
        TransactionCategory.id,
        TransactionCategory.name,
        TransactionCategory.color,
        sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0).label("total_spent"),
        sa.func.count(Transaction.id).label("tx_count"),
    ).join(
        Transaction, Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_90d,
        Transaction.date <= today,
    ).group_by(TransactionCategory.id, TransactionCategory.name, TransactionCategory.color).all()

    # Active budgets for target month
    curr_budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.year == year,
    ).all()
    curr_map = {b.category_id: round(b.amount_paise / 100.0, 2) for b in curr_budgets}

    essential_names = {
        "groceries", "food & dining", "utilities", "bills & utilities",
        "rent & housing", "housing", "transportation", "fuel", "healthcare"
    }

    items: list[BudgetRecommendationItem] = []
    total_suggested_inr = 0.0

    for row in cat_rows:
        # 3-month average
        monthly_avg_paise = int(round(row.total_spent / 3.0))
        monthly_avg_inr = round(monthly_avg_paise / 100.0, 2)

        is_ess = row.name.lower() in essential_names
        if is_ess:
            # +5% buffer
            suggested_inr = round(monthly_avg_inr * 1.05, 2)
            rationale = "Essential category: 3-month average + 5% inflation safety buffer."
        else:
            # -10% target optimization
            suggested_inr = round(max(500.0, monthly_avg_inr * 0.90), 2)
            rationale = "Discretionary category: 3-month average with 10% optimization savings target."

        suggested_paise = int(round(suggested_inr * 100))
        curr_b = curr_map.get(row.id)
        var_pct = round(((suggested_inr - (curr_b or monthly_avg_inr)) / (curr_b or monthly_avg_inr)) * 100.0, 1) if (curr_b or monthly_avg_inr) > 0 else 0.0

        total_suggested_inr += suggested_inr
        items.append(BudgetRecommendationItem(
            category_id=row.id,
            category_name=row.name,
            category_color=row.color,
            is_essential=is_ess,
            historical_avg_spent_inr=monthly_avg_inr,
            suggested_budget_inr=suggested_inr,
            suggested_budget_paise=suggested_paise,
            current_budget_inr=curr_b,
            variance_pct=var_pct,
            rationale=rationale,
        ))

    items.sort(key=lambda x: x.suggested_budget_inr, reverse=True)

    return BudgetRecommendationsResponse(
        month=month,
        year=year,
        total_suggested_inr=round(total_suggested_inr, 2),
        recommendations=items,
    )

def apply_budget_recommendations(
    db: Session,
    user_id: uuid.UUID,
    month: int,
    year: int,
    selected_category_ids: Optional[List[uuid.UUID]] = None,
) -> List[BudgetResponse]:
    """Bulk apply suggested budgets for month/year, allowing user override or selection."""
    recs = get_budget_recommendations(db, user_id, month, year)
    applied: List[BudgetResponse] = []

    target_items = recs.recommendations
    if selected_category_ids:
        id_set = set(selected_category_ids)
        target_items = [item for item in target_items if item.category_id in id_set]

    for item in target_items:
        existing = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == item.category_id,
            Budget.month == month,
            Budget.year == year,
        ).first()

        if existing:
            existing.amount_paise = item.suggested_budget_paise
        else:
            new_b = Budget(
                user_id=user_id,
                category_id=item.category_id,
                month=month,
                year=year,
                amount_paise=item.suggested_budget_paise,
                alert_threshold=0.80,
            )
            db.add(new_b)

    db.flush()
    return list_budgets(db, user_id, month, year)

