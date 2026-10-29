import uuid
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Tuple
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.account import FinancialAccount
from app.models.category import TransactionCategory
from app.schemas.dashboard import DashboardSummaryResponse, CashflowTrendItem, CategorySpendItem
from app.services.transaction_service import list_transactions

def get_period_dates(period: str) -> Tuple[date, date]:
    today = date.today()
    if period == "last_30_days":
        start_date = today - timedelta(days=30)
    elif period == "last_90_days":
        start_date = today - timedelta(days=90)
    elif period == "ytd":
        start_date = date(today.year, 1, 1)
    else:  # default "current_month"
        start_date = date(today.year, today.month, 1)
    return start_date, today

def get_dashboard_summary(db: Session, user_id: uuid.UUID, period: str = "current_month") -> DashboardSummaryResponse:
    """Compute real-time executive dashboard metrics for the authenticated user."""
    start_date, end_date = get_period_dates(period)

    # 1. Income & Expenses
    income_res = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "CREDIT",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).scalar() or 0

    expense_res = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).scalar() or 0

    net_savings = income_res - expense_res
    savings_rate = round((net_savings / income_res) * 100.0, 2) if income_res > 0 else 0.0

    # 2. Account balances
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
    ).all()

    liquid_paise = sum(a.balance_paise for a in accounts if a.account_type != "CREDIT_CARD")
    debt_paise = sum(a.balance_paise for a in accounts if a.account_type == "CREDIT_CARD")

    total_tx_count = db.query(sa.func.count(Transaction.id)).filter(
        Transaction.user_id == user_id
    ).scalar() or 0

    # 3. Simple initial health score calculation
    score = 50
    if savings_rate >= 20.0:
        score += 20
    elif savings_rate > 0.0:
        score += 10
    
    if liquid_paise > expense_res * 3:
        score += 20
    elif liquid_paise > expense_res:
        score += 10

    if debt_paise == 0:
        score += 10

    score = min(score, 100)
    if score >= 80:
        grade = "Excellent"
    elif score >= 65:
        grade = "Good"
    elif score >= 50:
        grade = "Fair"
    else:
        grade = "Needs Attention"

    # 4. Recent transactions
    recent_txs, _ = list_transactions(db, user_id=user_id, page=1, limit=5)

    return DashboardSummaryResponse(
        period=period,
        total_income_paise=income_res,
        total_income_inr=round(income_res / 100.0, 2),
        total_expenses_paise=expense_res,
        total_expenses_inr=round(expense_res / 100.0, 2),
        net_savings_paise=net_savings,
        net_savings_inr=round(net_savings / 100.0, 2),
        savings_rate=savings_rate,
        total_liquid_balance_paise=liquid_paise,
        total_liquid_balance_inr=round(liquid_paise / 100.0, 2),
        total_debt_balance_paise=debt_paise,
        total_debt_balance_inr=round(debt_paise / 100.0, 2),
        accounts_count=len(accounts),
        transactions_count=total_tx_count,
        health_score=score,
        health_grade=grade,
        recent_transactions=recent_txs,
    )

def get_cashflow_trend(db: Session, user_id: uuid.UUID, months: int = 6) -> List[CashflowTrendItem]:
    """Calculate monthly income and expense history for past N months."""
    today = date.today()
    results = []

    for i in range(months - 1, -1, -1):
        # Calculate year and month offset
        month_idx = today.month - i
        year_offset = today.year
        while month_idx <= 0:
            month_idx += 12
            year_offset -= 1

        start_dt = date(year_offset, month_idx, 1)
        if month_idx == 12:
            end_dt = date(year_offset + 1, 1, 1)
        else:
            end_dt = date(year_offset, month_idx + 1, 1)

        income = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "CREDIT",
            Transaction.date >= start_dt,
            Transaction.date < end_dt,
        ).scalar() or 0

        expense = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.date >= start_dt,
            Transaction.date < end_dt,
        ).scalar() or 0

        net = income - expense
        month_str = start_dt.strftime("%b %Y")

        results.append(
            CashflowTrendItem(
                month=month_str,
                income_paise=income,
                expenses_paise=expense,
                net_paise=net,
                income_inr=round(income / 100.0, 2),
                expenses_inr=round(expense / 100.0, 2),
                net_inr=round(net / 100.0, 2),
            )
        )

    return results

def get_category_breakdown(db: Session, user_id: uuid.UUID, period: str = "current_month") -> List[CategorySpendItem]:
    """Calculate expense distribution by category for the selected period."""
    start_date, end_date = get_period_dates(period)

    # Sum of all expenses in period
    total_expenses = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).scalar() or 0

    if total_expenses == 0:
        return []

    cat_spends = db.query(
        Transaction.category_id,
        TransactionCategory.name.label("category_name"),
        TransactionCategory.color.label("category_color"),
        sa.func.sum(Transaction.amount_paise).label("spent_paise")
    ).join(
        TransactionCategory, Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_date,
        Transaction.date <= end_date,
    ).group_by(
        Transaction.category_id, TransactionCategory.name, TransactionCategory.color
    ).order_by(
        sa.desc("spent_paise")
    ).all()

    items = []
    for row in cat_spends:
        spent = int(row.spent_paise)
        pct = round((spent / total_expenses) * 100.0, 1)
        items.append(
            CategorySpendItem(
                category_id=row.category_id,
                category_name=row.category_name,
                category_color=row.category_color or "#64748b",
                spent_paise=spent,
                spent_inr=round(spent / 100.0, 2),
                percentage=pct,
            )
        )

    return items
