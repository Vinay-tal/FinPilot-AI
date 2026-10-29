import uuid
import io
import csv
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Dict, Any, Tuple
import numpy as np
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.account import FinancialAccount
from app.models.category import TransactionCategory
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.models.recurring_transaction import RecurringTransaction
from app.models.financial_insight import FinancialInsight
from app.models.forecast import Forecast
from app.models.recommendation import Recommendation
from app.models.notification import UserNotification
from app.schemas.planning import (
    HealthFactorItem,
    HealthScoreResponse,
    CategoryReportItem,
    BudgetPerformanceReportItem,
    MonthlyReportResponse,
    NotificationResponse,
)

ESSENTIAL_CATEGORY_NAMES = {
    "groceries",
    "food & dining",
    "utilities",
    "bills & utilities",
    "rent & housing",
    "housing",
    "transportation",
    "fuel",
    "healthcare",
    "health & medical",
    "insurance",
}

def calculate_financial_health_score(db: Session, user_id: uuid.UUID) -> HealthScoreResponse:
    """
    Compute an explainable financial health score from 0 to 100 with documented,
    sub-factor normalization, missing data handling, and actionable improvement tips.
    Discloses that this is an educational heuristic, not a credit score.
    """
    today = date.today()
    start_90d = today - timedelta(days=90)
    start_30d = today - timedelta(days=30)

    # 1. Fetch Liquid & Debt Balances
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
    ).all()

    liquid_paise = sum(a.balance_paise for a in accounts if a.account_type != "CREDIT_CARD")
    debt_paise = sum(a.balance_paise for a in accounts if a.account_type == "CREDIT_CARD")
    liquid_inr = round(liquid_paise / 100.0, 2)
    debt_inr = round(debt_paise / 100.0, 2)

    # 2. Fetch 30-day Income and Expenses
    inc_30d = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "CREDIT",
        Transaction.date >= start_30d,
        Transaction.date <= today,
    ).scalar() or 0

    exp_30d = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_30d,
        Transaction.date <= today,
    ).scalar() or 0

    income_30d_inr = round(inc_30d / 100.0, 2)
    expense_30d_inr = round(exp_30d / 100.0, 2)
    net_savings_paise = inc_30d - exp_30d
    savings_rate_pct = round((net_savings_paise / inc_30d) * 100.0, 1) if inc_30d > 0 else 0.0

    # 3. Essential Monthly Expenses
    essential_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).join(
        TransactionCategory, Transaction.category_id == TransactionCategory.id, isouter=True
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_30d,
        Transaction.date <= today,
        sa.func.lower(TransactionCategory.name).in_(ESSENTIAL_CATEGORY_NAMES),
    ).scalar() or 0

    # If essential categories not explicitly tagged, estimate at 55% of monthly expenses
    if essential_paise == 0 and exp_30d > 0:
        essential_paise = int(exp_30d * 0.55)
    essential_inr = round(essential_paise / 100.0, 2)

    # 4. Active Budgets
    active_budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == today.month,
        Budget.year == today.year,
    ).all()

    # 5. Total Transactions Count & Months of History
    total_tx_count = db.query(sa.func.count(Transaction.id)).filter(
        Transaction.user_id == user_id
    ).scalar() or 0

    earliest_tx = db.query(sa.func.min(Transaction.date)).filter(
        Transaction.user_id == user_id
    ).scalar()
    history_days = (today - earliest_tx).days if earliest_tx else 0

    # --- FACTOR EVALUATIONS ---
    factors: List[HealthFactorItem] = []

    # Factor 1: Savings Rate (Weight 20)
    sr_score = 0.0
    if savings_rate_pct >= 25.0:
        sr_score = 20.0
    elif savings_rate_pct >= 20.0:
        sr_score = 18.0
    elif savings_rate_pct >= 15.0:
        sr_score = 14.0
    elif savings_rate_pct >= 10.0:
        sr_score = 10.0
    elif savings_rate_pct >= 5.0:
        sr_score = 6.0
    elif savings_rate_pct > 0.0:
        sr_score = 3.0
    else:
        sr_score = 0.0

    factors.append(HealthFactorItem(
        factor_id="savings_rate",
        name="Savings Rate",
        weight=20,
        score=sr_score,
        max_score=20.0,
        normalized_pct=round((sr_score / 20.0) * 100.0, 1),
        metric_value=f"{savings_rate_pct}%",
        calculation_details=f"Net monthly savings (₹{round(net_savings_paise/100, 2):,}) / Monthly income (₹{income_30d_inr:,})",
        actionable_tip="Target allocating at least 20% of net monthly income to savings and investments.",
    ))

    # Factor 2: Essential Expense Coverage (Weight 20)
    monthly_ess = max(essential_inr, 1000.0)
    coverage_months = round(liquid_inr / monthly_ess, 1) if monthly_ess > 0 else 0.0
    eec_score = 0.0
    if coverage_months >= 6.0:
        eec_score = 20.0
    elif coverage_months >= 4.0:
        eec_score = 17.0
    elif coverage_months >= 3.0:
        eec_score = 14.0
    elif coverage_months >= 2.0:
        eec_score = 10.0
    elif coverage_months >= 1.0:
        eec_score = 6.0
    else:
        eec_score = 2.0

    factors.append(HealthFactorItem(
        factor_id="essential_coverage",
        name="Essential-Expense Coverage",
        weight=20,
        score=eec_score,
        max_score=20.0,
        normalized_pct=round((eec_score / 20.0) * 100.0, 1),
        metric_value=f"{coverage_months} months",
        calculation_details=f"Liquid cash (₹{liquid_inr:,}) / Monthly essential expenses (₹{essential_inr:,})",
        actionable_tip="Maintain at least 3 to 6 months of essential living expenses in liquid accounts.",
    ))

    # Factor 3: Emergency Reserve Coverage (Weight 20)
    # Target benchmark: 3x total monthly expenses or ₹1,00,000 floor
    reserve_target = max(expense_30d_inr * 3.0, 100000.0)
    reserve_ratio = round((liquid_inr / reserve_target) * 100.0, 1) if reserve_target > 0 else 0.0
    erc_score = 0.0
    if reserve_ratio >= 100.0:
        erc_score = 20.0
    elif reserve_ratio >= 75.0:
        erc_score = 16.0
    elif reserve_ratio >= 50.0:
        erc_score = 12.0
    elif reserve_ratio >= 25.0:
        erc_score = 7.0
    else:
        erc_score = 2.0

    factors.append(HealthFactorItem(
        factor_id="emergency_reserve",
        name="Emergency Reserve Coverage",
        weight=20,
        score=erc_score,
        max_score=20.0,
        normalized_pct=round((erc_score / 20.0) * 100.0, 1),
        metric_value=f"{reserve_ratio}% of target",
        calculation_details=f"Liquid assets (₹{liquid_inr:,}) / 3-month safety benchmark (₹{round(reserve_target, 2):,})",
        actionable_tip="Consistently channel monthly surpluses into liquid reserves until reaching 100% of safety target.",
    ))

    # Factor 4: Budget Adherence (Weight 20)
    if not active_budgets:
        factors.append(HealthFactorItem(
            factor_id="budget_adherence",
            name="Budget Adherence",
            weight=20,
            score=0.0,
            max_score=20.0,
            normalized_pct=0.0,
            is_excluded=True,
            exclusion_reason="No monthly category budgets configured for current period.",
            metric_value="Not configured",
            calculation_details="Requires at least 1 active category budget allocation.",
            actionable_tip="Create monthly category budgets to unlock proactive pacing and adherence scoring.",
        ))
    else:
        # Check how many categories exceeded budget
        overspent_count = 0
        for b in active_budgets:
            spent = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.category_id == b.category_id,
                Transaction.transaction_type == "DEBIT",
                Transaction.date >= date(today.year, today.month, 1),
                Transaction.date <= today,
            ).scalar() or 0
            if spent > b.amount_paise:
                overspent_count += 1

        ba_score = 0.0
        if overspent_count == 0:
            ba_score = 20.0
        elif overspent_count == 1:
            ba_score = 14.0
        elif overspent_count == 2:
            ba_score = 8.0
        else:
            ba_score = 2.0

        factors.append(HealthFactorItem(
            factor_id="budget_adherence",
            name="Budget Adherence",
            weight=20,
            score=ba_score,
            max_score=20.0,
            normalized_pct=round((ba_score / 20.0) * 100.0, 1),
            metric_value=f"{len(active_budgets) - overspent_count}/{len(active_budgets)} on track",
            calculation_details=f"{overspent_count} categories exceeded out of {len(active_budgets)} active category budgets.",
            actionable_tip="Review categories exceeding pacing threshold and reduce discretionary outlays.",
        ))

    # Factor 5: Debt Payment Burden (Weight 10 - Only if debt data is available)
    has_debt_account = any(a.account_type == "CREDIT_CARD" for a in accounts)
    recurring_emis = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
        sa.or_(
            sa.func.lower(RecurringTransaction.name).like("%emi%"),
            sa.func.lower(RecurringTransaction.name).like("%loan%"),
        ),
    ).all()
    monthly_emi_paise = sum(r.expected_amount_paise for r in recurring_emis)
    monthly_emi_inr = round(monthly_emi_paise / 100.0, 2)

    if not has_debt_account and monthly_emi_inr == 0:
        factors.append(HealthFactorItem(
            factor_id="debt_burden",
            name="Debt Payment Burden",
            weight=10,
            score=0.0,
            max_score=10.0,
            normalized_pct=0.0,
            is_excluded=True,
            exclusion_reason="No credit card balance or active loan EMIs detected.",
            metric_value="Zero debt detected",
            calculation_details="Excluded from weighting because user has no documented debt liabilities.",
            actionable_tip="Continue maintaining a zero-debt or low-interest lifestyle.",
        ))
    else:
        # Debt-to-income (DTI) or debt ratio
        monthly_debt_service = monthly_emi_inr + (debt_inr * 0.05)  # 5% min due
        dti_pct = round((monthly_debt_service / max(income_30d_inr, 1000.0)) * 100.0, 1)
        debt_score = 0.0
        if dti_pct <= 10.0:
            debt_score = 10.0
        elif dti_pct <= 25.0:
            debt_score = 7.0
        elif dti_pct <= 40.0:
            debt_score = 4.0
        else:
            debt_score = 1.0

        factors.append(HealthFactorItem(
            factor_id="debt_burden",
            name="Debt Payment Burden",
            weight=10,
            score=debt_score,
            max_score=10.0,
            normalized_pct=round((debt_score / 10.0) * 100.0, 1),
            metric_value=f"{dti_pct}% DTI",
            calculation_details=f"Monthly debt obligation (₹{round(monthly_debt_service, 2):,}) / Monthly income (₹{income_30d_inr:,})",
            actionable_tip="Keep total monthly debt payments below 20% of net monthly take-home.",
        ))

    # Factor 6: Income & Spending Stability (Weight 10)
    if history_days < 45 or total_tx_count < 10:
        factors.append(HealthFactorItem(
            factor_id="stability",
            name="Income & Spending Stability",
            weight=10,
            score=0.0,
            max_score=10.0,
            normalized_pct=0.0,
            is_excluded=True,
            exclusion_reason="Requires at least 45 days and 10+ transactions to evaluate cash flow variance.",
            metric_value="Insufficient history",
            calculation_details=f"Current history: {history_days} days, {total_tx_count} transactions.",
            actionable_tip="Continue recording daily transactions to unlock stability variance scoring.",
        ))
    else:
        # Calculate monthly cash flows over last 3 months
        monthly_net_flows = []
        for offset in [0, 1, 2]:
            m = today.month - offset
            y = today.year
            if m <= 0:
                m += 12
                y -= 1
            s_dt = date(y, m, 1)
            e_dt = date(y, m + 1, 1) if m < 12 else date(y + 1, 1, 1)
            m_inc = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "CREDIT",
                Transaction.date >= s_dt,
                Transaction.date < e_dt,
            ).scalar() or 0
            m_exp = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
                Transaction.user_id == user_id,
                Transaction.transaction_type == "DEBIT",
                Transaction.date >= s_dt,
                Transaction.date < e_dt,
            ).scalar() or 0
            monthly_net_flows.append((m_inc - m_exp) / 100.0)

        # Standard deviation & mean of net flows
        mean_flow = float(np.mean(monthly_net_flows))
        std_flow = float(np.std(monthly_net_flows))
        cv = (std_flow / abs(mean_flow)) if abs(mean_flow) > 100.0 else 0.25

        stab_score = 0.0
        if cv < 0.20:
            stab_score = 10.0
        elif cv < 0.40:
            stab_score = 7.0
        elif cv < 0.65:
            stab_score = 5.0
        else:
            stab_score = 2.0

        factors.append(HealthFactorItem(
            factor_id="stability",
            name="Income & Spending Stability",
            weight=10,
            score=stab_score,
            max_score=10.0,
            normalized_pct=round((stab_score / 10.0) * 100.0, 1),
            metric_value=f"Volatility: {round(cv, 2)}",
            calculation_details=f"Cash flow std dev ₹{round(std_flow, 2):,} across 3-month rolling window.",
            actionable_tip="Smooth discretionary outlays month-to-month to minimize cash flow volatility.",
        ))

    # --- NORMALIZATION & OVERALL SCORE ---
    included_factors = [f for f in factors if not f.is_excluded]
    total_included_weight = sum(f.weight for f in included_factors)
    raw_score_sum = sum(f.score for f in included_factors)

    if total_included_weight > 0:
        overall_score = int(round((raw_score_sum / total_included_weight) * 100.0))
    else:
        overall_score = 50

    overall_score = max(0, min(100, overall_score))

    if overall_score >= 80:
        grade = "Excellent"
        summary_text = "Strong financial foundation with robust liquidity and healthy savings habits."
    elif overall_score >= 65:
        grade = "Good"
        summary_text = "Solid financial position with minor areas for savings or budget optimization."
    elif overall_score >= 50:
        grade = "Fair"
        summary_text = "Moderate financial stability; building emergency buffer and curbing overspending will boost resilience."
    else:
        grade = "Needs Attention"
        summary_text = "Cash flow or liquidity requires attention; focus on emergency reserves and capping discretionary debt."

    # Top improvement actions
    actions: List[str] = []
    # Sort included factors by lowest normalized pct
    sorted_factors = sorted(included_factors, key=lambda f: f.normalized_pct)
    for f in sorted_factors[:3]:
        if f.normalized_pct < 80.0:
            actions.append(f"{f.name}: {f.actionable_tip}")

    if not actions:
        actions.append("All assessed factors are performing strongly. Continue your consistent savings momentum!")

    return HealthScoreResponse(
        overall_score=overall_score,
        grade=grade,
        summary=summary_text,
        liquid_reserve_inr=liquid_inr,
        monthly_expenses_inr=expense_30d_inr,
        savings_rate_pct=savings_rate_pct,
        factors=factors,
        excluded_factors_count=len([f for f in factors if f.is_excluded]),
        top_improvement_actions=actions,
    )

def generate_monthly_report(db: Session, user_id: uuid.UUID, month: int, year: int) -> MonthlyReportResponse:
    """Generate consolidated monthly report dossier."""
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    # 1. Income & Expenses
    income_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "CREDIT",
        Transaction.date >= start_date,
        Transaction.date < end_date,
    ).scalar() or 0

    expense_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_date,
        Transaction.date < end_date,
    ).scalar() or 0

    total_inc_inr = round(income_paise / 100.0, 2)
    total_exp_inr = round(expense_paise / 100.0, 2)
    net_savings_inr = round((income_paise - expense_paise) / 100.0, 2)
    savings_rate_pct = round((net_savings_inr / total_inc_inr) * 100.0, 1) if total_inc_inr > 0 else 0.0

    # 2. Account Balances
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
    ).all()
    liquid_inr = round(sum(a.balance_paise for a in accounts if a.account_type != "CREDIT_CARD") / 100.0, 2)

    tx_count = db.query(sa.func.count(Transaction.id)).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.date < end_date,
    ).scalar() or 0

    # 3. Category Breakdown with MoM change
    # Prior month dates
    pm_month = 12 if month == 1 else month - 1
    pm_year = year - 1 if month == 1 else year
    pm_start = date(pm_year, pm_month, 1)
    pm_end = start_date

    cat_rows = db.query(
        TransactionCategory.id,
        TransactionCategory.name,
        TransactionCategory.color,
        sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0).label("spent")
    ).join(
        Transaction, Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_date,
        Transaction.date < end_date,
    ).group_by(TransactionCategory.id, TransactionCategory.name, TransactionCategory.color).all()

    pm_cat_rows = db.query(
        TransactionCategory.id,
        sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0).label("pm_spent")
    ).join(
        Transaction, Transaction.category_id == TransactionCategory.id
    ).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= pm_start,
        Transaction.date < pm_end,
    ).group_by(TransactionCategory.id).all()
    pm_cat_map = {row.id: int(row.pm_spent) for row in pm_cat_rows}

    category_items: List[CategoryReportItem] = []
    for c in cat_rows:
        spent_inr = round(c.spent / 100.0, 2)
        share = round((c.spent / expense_paise) * 100.0, 1) if expense_paise > 0 else 0.0
        pm_spent = pm_cat_map.get(c.id, 0)
        pm_spent_inr = round(pm_spent / 100.0, 2)
        diff_inr = round(spent_inr - pm_spent_inr, 2)
        diff_pct = round((diff_inr / pm_spent_inr) * 100.0, 1) if pm_spent_inr > 0 else 0.0

        category_items.append(CategoryReportItem(
            category_name=c.name,
            category_color=c.color,
            spent_inr=spent_inr,
            share_pct=share,
            mom_change_inr=diff_inr,
            mom_change_pct=diff_pct,
        ))
    category_items.sort(key=lambda x: x.spent_inr, reverse=True)

    # 4. Budget Performance
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == month,
        Budget.year == year,
    ).all()

    budget_items: List[BudgetPerformanceReportItem] = []
    tot_budgeted_inr = 0.0
    tot_budget_spent_inr = 0.0

    for b in budgets:
        b_cat_name = b.category.name if b.category else "Uncategorized"
        b_inr = round(b.amount_paise / 100.0, 2)
        tot_budgeted_inr += b_inr

        # Find spend
        b_spent_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == b.category_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.date >= start_date,
            Transaction.date < end_date,
        ).scalar() or 0
        b_spent_inr = round(b_spent_paise / 100.0, 2)
        tot_budget_spent_inr += b_spent_inr

        var_inr = round(b_inr - b_spent_inr, 2)
        pacing = round((b_spent_inr / b_inr) * 100.0, 1) if b_inr > 0 else 0.0
        stat = "ON_TRACK" if b_spent_inr <= b_inr else "EXCEEDED"

        budget_items.append(BudgetPerformanceReportItem(
            category_name=b_cat_name,
            budgeted_inr=b_inr,
            spent_inr=b_spent_inr,
            variance_inr=var_inr,
            pacing_pct=pacing,
            status=stat,
        ))

    budget_util_pct = round((tot_budget_spent_inr / tot_budgeted_inr) * 100.0, 1) if tot_budgeted_inr > 0 else 0.0

    # 5. Forecast vs Actual
    latest_fc = db.query(Forecast).filter(
        Forecast.user_id == user_id,
    ).order_by(Forecast.forecast_date.desc()).first()
    fc_balance = round(latest_fc.predicted_balance_paise / 100.0, 2) if latest_fc else None
    actual_vs_fc = round(liquid_inr - fc_balance, 2) if fc_balance is not None else None

    # 6. Anomalies Detected
    anomalies = db.query(FinancialInsight).filter(
        FinancialInsight.user_id == user_id,
        FinancialInsight.insight_type.in_(["ANOMALY", "SPENDING_SPIKE"]),
        FinancialInsight.created_at >= datetime(year, month, 1, tzinfo=timezone.utc),
    ).all()
    anomaly_titles = [f"{a.title} ({a.severity})" for a in anomalies]

    # 7. Recommendation Summary
    recs = db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
    ).all()
    rec_summary = {
        "new": sum(1 for r in recs if r.status == "new"),
        "accepted": sum(1 for r in recs if r.status == "accepted"),
        "completed": sum(1 for r in recs if r.status == "completed"),
        "dismissed": sum(1 for r in recs if r.status == "dismissed"),
    }

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    month_label = f"{month_names[month - 1]} {year}"

    return MonthlyReportResponse(
        month=month,
        year=year,
        month_label=month_label,
        total_income_inr=total_inc_inr,
        total_expenses_inr=total_exp_inr,
        net_savings_inr=net_savings_inr,
        savings_rate_pct=savings_rate_pct,
        total_liquid_balance_inr=liquid_inr,
        accounts_count=len(accounts),
        transactions_count=tx_count,
        category_breakdown=category_items,
        budget_performance=budget_items,
        total_budgeted_inr=round(tot_budgeted_inr, 2),
        total_budget_spent_inr=round(tot_budget_spent_inr, 2),
        budget_utilization_pct=budget_util_pct,
        forecast_month_end_balance_inr=fc_balance,
        actual_vs_forecast_delta_inr=actual_vs_fc,
        anomalies_detected=anomaly_titles,
        recommendation_summary=rec_summary,
        generated_at=datetime.now(timezone.utc),
    )

def sanitize_csv_cell(val: Any) -> str:
    """Defend against CSV/Formula injection in spreadsheet applications."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s

def export_monthly_report_csv(db: Session, user_id: uuid.UUID, month: int, year: int) -> str:
    """Generate CSV string for monthly report data with formula injection defense."""
    rep = generate_monthly_report(db, user_id, month, year)
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["# FinPilot AI Monthly Financial Report"])
    writer.writerow(["Month", sanitize_csv_cell(rep.month_label)])
    writer.writerow(["Generated At", rep.generated_at.isoformat()])
    writer.writerow([])

    writer.writerow(["--- Executive Summary ---"])
    writer.writerow(["Total Income (INR)", rep.total_income_inr])
    writer.writerow(["Total Expenses (INR)", rep.total_expenses_inr])
    writer.writerow(["Net Savings (INR)", rep.net_savings_inr])
    writer.writerow(["Savings Rate (%)", f"{rep.savings_rate_pct}%"])
    writer.writerow(["Total Liquid Balance (INR)", rep.total_liquid_balance_inr])
    writer.writerow(["Transactions Count", rep.transactions_count])
    writer.writerow(["Budget Utilization (%)", f"{rep.budget_utilization_pct}%"])
    if rep.forecast_month_end_balance_inr is not None:
        writer.writerow(["Forecasted Balance (INR)", rep.forecast_month_end_balance_inr])
    writer.writerow([])

    writer.writerow(["--- Category Breakdown ---"])
    writer.writerow(["Category", "Spent (INR)", "Share (%)", "MoM Change (INR)", "MoM Change (%)"])
    for c in rep.category_breakdown:
        writer.writerow([sanitize_csv_cell(c.category_name), c.spent_inr, f"{c.share_pct}%", c.mom_change_inr, f"{c.mom_change_pct}%"])
    writer.writerow([])

    writer.writerow(["--- Budget Performance ---"])
    writer.writerow(["Category", "Budgeted (INR)", "Spent (INR)", "Variance (INR)", "Pacing (%)", "Status"])
    for b in rep.budget_performance:
        writer.writerow([sanitize_csv_cell(b.category_name), b.budgeted_inr, b.spent_inr, b.variance_inr, f"{b.pacing_pct}%", sanitize_csv_cell(b.status)])
    writer.writerow([])

    writer.writerow(["--- Anomalies Detected ---"])
    if rep.anomalies_detected:
        for a in rep.anomalies_detected:
            writer.writerow([sanitize_csv_cell(a)])
    else:
        writer.writerow(["No anomalies detected during this period."])

    return output.getvalue()

def generate_system_alerts(db: Session, user_id: uuid.UUID) -> List[NotificationResponse]:
    """
    Evaluate spending conditions and emit configurable in-app notifications
    for budget thresholds, anomalies, and forecasted cash shortages.
    """
    today = date.today()
    created_alerts: List[UserNotification] = []

    # 1. Budget Threshold Alerts (80% warning, 100% exceeded)
    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == today.month,
        Budget.year == today.year,
    ).all()

    for b in budgets:
        spent_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == b.category_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.date >= date(today.year, today.month, 1),
            Transaction.date <= today,
        ).scalar() or 0
        cat_name = b.category.name if b.category else "Category"

        if spent_paise >= b.amount_paise:
            # Check if alert already sent recently
            existing = db.query(UserNotification).filter(
                UserNotification.user_id == user_id,
                UserNotification.title == f"Budget Exceeded: {cat_name}",
            ).first()
            if not existing:
                note = UserNotification(
                    user_id=user_id,
                    title=f"Budget Exceeded: {cat_name}",
                    message=f"You have spent ₹{round(spent_paise/100, 2):,}, exceeding your ₹{round(b.amount_paise/100, 2):,} monthly limit.",
                    notification_type="ALERT",
                    action_url="/budgets",
                )
                db.add(note)
                created_alerts.append(note)
        elif (spent_paise / b.amount_paise) >= float(b.alert_threshold or 0.80):
            existing = db.query(UserNotification).filter(
                UserNotification.user_id == user_id,
                UserNotification.title == f"Budget Warning: {cat_name}",
            ).first()
            if not existing:
                note = UserNotification(
                    user_id=user_id,
                    title=f"Budget Warning: {cat_name}",
                    message=f"You have reached {round((spent_paise/b.amount_paise)*100, 1)}% of your monthly allocation for {cat_name}.",
                    notification_type="ALERT",
                    action_url="/budgets",
                )
                db.add(note)
                created_alerts.append(note)

    # 2. Forecast Shortfall Warning
    latest_fc = db.query(Forecast).filter(
        Forecast.user_id == user_id,
    ).order_by(Forecast.forecast_date.desc()).first()

    if latest_fc and latest_fc.predicted_balance_paise < 2500000:  # < ₹25,000
        existing = db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.title == "Low Cash Reserve Forecasted",
        ).first()
        if not existing:
            note = UserNotification(
                user_id=user_id,
                title="Low Cash Reserve Forecasted",
                message=f"Predicted month-end balance is ₹{round(latest_fc.predicted_balance_paise/100, 2):,}. Consider curbing discretionary expenses.",
                notification_type="ALERT",
                action_url="/forecasting",
            )
            db.add(note)
            created_alerts.append(note)

    db.flush()

    # Return active notifications
    all_notes = db.query(UserNotification).filter(
        UserNotification.user_id == user_id
    ).order_by(UserNotification.created_at.desc()).limit(20).all()

    return [NotificationResponse.model_validate(n) for n in all_notes]
