import uuid
from datetime import date, datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.category import TransactionCategory
from app.models.account import FinancialAccount
from app.models.recurring_transaction import RecurringTransaction
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.services.dashboard_service import get_dashboard_summary, get_category_breakdown
from app.services.forecasting_service import generate_forecast_service
from app.ml.copilot.guardrails import sanitize_user_input, wrap_untrusted_data

# ============================================================================
# Tool 1: Query Aggregate Transactions
# ============================================================================

class QueryTransactionsInput(BaseModel):
    start_date: Optional[str] = Field(None, description="ISO start date YYYY-MM-DD. Defaults to 1st of current month if None.")
    end_date: Optional[str] = Field(None, description="ISO end date YYYY-MM-DD. Defaults to today if None.")
    category_slug: Optional[str] = Field(None, description="Slug or keyword for category (e.g. 'food-dining', 'groceries', 'transport', 'shopping').")
    transaction_type: Optional[str] = Field("DEBIT", description="Movement direction: 'DEBIT', 'CREDIT', or 'ALL'. Defaults to 'DEBIT'.")
    merchant_keyword: Optional[str] = Field(None, description="Optional merchant name filter (e.g. 'Swiggy', 'Amazon', 'Uber').")

def execute_query_transactions(db: Session, user_id: uuid.UUID, params: QueryTransactionsInput) -> Dict[str, Any]:
    today = date.today()
    try:
        s_date = date.fromisoformat(params.start_date) if params.start_date else date(today.year, today.month, 1)
    except Exception:
        s_date = date(today.year, today.month, 1)

    try:
        e_date = date.fromisoformat(params.end_date) if params.end_date else today
    except Exception:
        e_date = today

    q = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= s_date,
        Transaction.date <= e_date,
    )

    if params.transaction_type and params.transaction_type.upper() in ["DEBIT", "CREDIT"]:
        q = q.filter(Transaction.transaction_type == params.transaction_type.upper())

    matched_category_name = None
    if params.category_slug:
        cat_term = params.category_slug.lower().strip()
        cat = db.query(TransactionCategory).filter(
            sa.or_(
                TransactionCategory.slug.ilike(f"%{cat_term}%"),
                TransactionCategory.name.ilike(f"%{cat_term}%"),
            )
        ).first()
        if cat:
            q = q.filter(Transaction.category_id == cat.id)
            matched_category_name = cat.name

    if params.merchant_keyword:
        q = q.filter(
            sa.or_(
                Transaction.merchant_name.ilike(f"%{params.merchant_keyword}%"),
                Transaction.narration.ilike(f"%{params.merchant_keyword}%"),
            )
        )

    txs = q.order_by(Transaction.date.desc()).all()
    total_paise = sum(t.amount_paise for t in txs)
    total_inr = round(total_paise / 100.0, 2)
    count = len(txs)
    avg_inr = round(total_inr / count, 2) if count > 0 else 0.0

    # Merchant frequency & spend breakdown
    merchant_totals: Dict[str, float] = {}
    for t in txs:
        m_name = t.merchant_name or t.narration[:25]
        merchant_totals[m_name] = merchant_totals.get(m_name, 0.0) + (t.amount_paise / 100.0)

    top_merchants = [
        {"merchant": sanitize_user_input(k[:30]), "total_spent_inr": round(v, 2)}
        for k, v in sorted(merchant_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    return {
        "start_date": s_date.isoformat(),
        "end_date": e_date.isoformat(),
        "category_name": matched_category_name or params.category_slug or "All Categories",
        "transaction_type": params.transaction_type or "DEBIT",
        "total_amount_inr": total_inr,
        "transaction_count": count,
        "average_amount_inr": avg_inr,
        "top_merchants": top_merchants,
        "recent_samples": [
            {
                "date": t.date.isoformat(),
                "merchant": sanitize_user_input(t.merchant_name or t.narration[:30]),
                "amount_inr": round(t.amount_paise / 100.0, 2),
                "type": t.transaction_type,
            }
            for t in txs[:3]
        ],
    }

# ============================================================================
# Tool 2: Compare Time Periods
# ============================================================================

class ComparePeriodsInput(BaseModel):
    period_type: str = Field("month_over_month", description="Comparison mode: 'month_over_month' or 'custom'.")
    p1_start: Optional[str] = Field(None, description="Period 1 start (current)")
    p1_end: Optional[str] = Field(None, description="Period 1 end (current)")
    p2_start: Optional[str] = Field(None, description="Period 2 start (previous)")
    p2_end: Optional[str] = Field(None, description="Period 2 end (previous)")

def execute_compare_periods(db: Session, user_id: uuid.UUID, params: ComparePeriodsInput) -> Dict[str, Any]:
    today = date.today()
    # Month over month default
    if params.period_type == "month_over_month" or not params.p1_start:
        p1_start = date(today.year, today.month, 1)
        p1_end = today
        # Last month same days
        first_of_this_month = date(today.year, today.month, 1)
        last_day_of_prev_month = first_of_this_month - timedelta(days=1)
        p2_start = date(last_day_of_prev_month.year, last_day_of_prev_month.month, 1)
        p2_end = date(last_day_of_prev_month.year, last_day_of_prev_month.month, min(today.day, last_day_of_prev_month.day))
    else:
        p1_start = date.fromisoformat(params.p1_start)
        p1_end = date.fromisoformat(params.p1_end) if params.p1_end else today
        p2_start = date.fromisoformat(params.p2_start)
        p2_end = date.fromisoformat(params.p2_end)

    # Categories list
    categories = db.query(TransactionCategory).filter(TransactionCategory.is_income == False).all()

    category_comparisons = []
    total_p1_paise = 0
    total_p2_paise = 0

    for cat in categories:
        p1_sum = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == cat.id,
            Transaction.transaction_type == "DEBIT",
            Transaction.date >= p1_start,
            Transaction.date <= p1_end,
        ).scalar() or 0

        p2_sum = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == cat.id,
            Transaction.transaction_type == "DEBIT",
            Transaction.date >= p2_start,
            Transaction.date <= p2_end,
        ).scalar() or 0

        total_p1_paise += p1_sum
        total_p2_paise += p2_sum

        if p1_sum > 0 or p2_sum > 0:
            p1_inr = round(p1_sum / 100.0, 2)
            p2_inr = round(p2_sum / 100.0, 2)
            delta_inr = round(p1_inr - p2_inr, 2)
            pct_change = round(((p1_inr - p2_inr) / p2_inr) * 100.0, 1) if p2_inr > 0 else (100.0 if p1_inr > 0 else 0.0)

            category_comparisons.append({
                "category_id": str(cat.id),
                "category_name": cat.name,
                "current_period_inr": p1_inr,
                "previous_period_inr": p2_inr,
                "delta_inr": delta_inr,
                "percentage_change": pct_change,
            })

    # Sort by highest increase in spending
    category_comparisons.sort(key=lambda x: x["delta_inr"], reverse=True)

    total_p1_inr = round(total_p1_paise / 100.0, 2)
    total_p2_inr = round(total_p2_paise / 100.0, 2)
    total_delta_inr = round(total_p1_inr - total_p2_inr, 2)
    total_pct_change = round(((total_p1_inr - total_p2_inr) / total_p2_inr) * 100.0, 1) if total_p2_inr > 0 else 0.0

    return {
        "current_period": f"{p1_start.isoformat()} to {p1_end.isoformat()}",
        "previous_period": f"{p2_start.isoformat()} to {p2_end.isoformat()}",
        "current_total_expenses_inr": total_p1_inr,
        "previous_total_expenses_inr": total_p2_inr,
        "net_delta_inr": total_delta_inr,
        "net_percentage_change": total_pct_change,
        "highest_increasing_categories": category_comparisons[:3],
        "all_category_changes": category_comparisons,
    }

# ============================================================================
# Tool 3: Get Recurring Payments
# ============================================================================

class GetRecurringInput(BaseModel):
    due_within_days: int = Field(30, description="Window of upcoming days to inspect. Defaults to 30.")
    transaction_type: Optional[str] = Field(None, description="Filter by 'DEBIT' (expenses/bills) or 'CREDIT' (salary).")

def execute_get_recurring(db: Session, user_id: uuid.UUID, params: GetRecurringInput) -> Dict[str, Any]:
    today = date.today()
    cutoff_date = today + timedelta(days=params.due_within_days)

    q = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
    )
    if params.transaction_type and params.transaction_type.upper() in ["DEBIT", "CREDIT"]:
        q = q.filter(RecurringTransaction.transaction_type == params.transaction_type.upper())

    items = q.all()

    upcoming_list = []
    total_upcoming_debits_paise = 0
    total_upcoming_credits_paise = 0

    for item in items:
        # Determine next due date
        next_d = item.next_expected_date or today
        days_until = (next_d - today).days

        if next_d <= cutoff_date:
            amt_inr = round(item.amount_paise / 100.0, 2)
            if item.transaction_type == "DEBIT":
                total_upcoming_debits_paise += item.amount_paise
            else:
                total_upcoming_credits_paise += item.amount_paise

            upcoming_list.append({
                "id": str(item.id),
                "name": item.merchant_name or item.narration_pattern,
                "amount_inr": amt_inr,
                "transaction_type": item.transaction_type,
                "frequency": item.frequency,
                "next_expected_date": next_d.isoformat(),
                "days_until_due": days_until,
                "is_overdue": days_until < 0,
            })

    # Sort by nearest due date
    upcoming_list.sort(key=lambda x: x["days_until_due"])

    return {
        "horizon_days": params.due_within_days,
        "total_upcoming_bills_inr": round(total_upcoming_debits_paise / 100.0, 2),
        "total_upcoming_income_inr": round(total_upcoming_credits_paise / 100.0, 2),
        "recurring_payments": upcoming_list,
    }

# ============================================================================
# Tool 4: Budget and Goals Progress
# ============================================================================

class GetBudgetAndGoalsInput(BaseModel):
    include_goals: bool = Field(True, description="Whether to include active savings goals.")

def execute_get_budget_and_goals(db: Session, user_id: uuid.UUID, params: GetBudgetAndGoalsInput) -> Dict[str, Any]:
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    budgets = db.query(Budget).filter(
        Budget.user_id == user_id,
        Budget.month == today.month,
        Budget.year == today.year,
    ).all()

    budget_items = []
    total_budget_limit_paise = 0
    total_budget_spent_paise = 0

    for b in budgets:
        # Calculate spent this month for this category
        spent_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
            Transaction.user_id == user_id,
            Transaction.category_id == b.category_id,
            Transaction.transaction_type == "DEBIT",
            Transaction.date >= start_of_month,
            Transaction.date <= today,
        ).scalar() or 0

        limit_inr = round(b.limit_paise / 100.0, 2)
        spent_inr = round(spent_paise / 100.0, 2)
        remaining_inr = round(max(0, b.limit_paise - spent_paise) / 100.0, 2)
        pct_used = round((spent_paise / b.limit_paise) * 100.0, 1) if b.limit_paise > 0 else 0.0

        total_budget_limit_paise += b.limit_paise
        total_budget_spent_paise += spent_paise

        cat = db.query(TransactionCategory).filter(TransactionCategory.id == b.category_id).first()
        cat_name = cat.name if cat else "Uncategorized"

        budget_items.append({
            "category_name": cat_name,
            "monthly_limit_inr": limit_inr,
            "spent_inr": spent_inr,
            "remaining_inr": remaining_inr,
            "percent_used": pct_used,
            "is_exceeded": spent_paise > b.limit_paise,
        })

    # Goals
    goal_items = []
    if params.include_goals:
        goals = db.query(SavingsGoal).filter(
            SavingsGoal.user_id == user_id,
            SavingsGoal.is_active == True,
        ).all()
        for g in goals:
            target_inr = round(g.target_amount_paise / 100.0, 2)
            current_inr = round(g.current_saved_paise / 100.0, 2)
            progress_pct = round((g.current_saved_paise / g.target_amount_paise) * 100.0, 1) if g.target_amount_paise > 0 else 0.0
            goal_items.append({
                "goal_name": g.name,
                "target_amount_inr": target_inr,
                "current_saved_inr": current_inr,
                "progress_pct": progress_pct,
                "target_date": g.target_date.isoformat() if g.target_date else None,
            })

    return {
        "month": today.strftime("%B %Y"),
        "total_budgeted_limit_inr": round(total_budget_limit_paise / 100.0, 2),
        "total_budgeted_spent_inr": round(total_budget_spent_paise / 100.0, 2),
        "overall_utilization_pct": round((total_budget_spent_paise / total_budget_limit_paise) * 100.0, 1) if total_budget_limit_paise > 0 else 0.0,
        "budgets": budget_items,
        "goals": goal_items,
    }

# ============================================================================
# Tool 5: Get Cash-Flow Forecast
# ============================================================================

class GetCashflowForecastInput(BaseModel):
    horizon_days: int = Field(30, description="Forecast horizon in days (30, 60, or 90).")

def execute_get_forecast(db: Session, user_id: uuid.UUID, params: GetCashflowForecastInput) -> Dict[str, Any]:
    forecast_data = generate_forecast_service(
        db,
        user_id,
        horizon_days=params.horizon_days,
        model_type="auto",
        reserve_threshold_inr=10000.0,
    )

    risk_info = forecast_data.get("risk_analysis", {})
    explanation = forecast_data.get("explanation", {})

    return {
        "model_version": forecast_data.get("model_version"),
        "horizon_days": forecast_data.get("horizon_days"),
        "current_liquid_balance_inr": forecast_data.get("current_balance_inr"),
        "predicted_end_balance_inr": forecast_data.get("projected_end_balance_inr"),
        "minimum_projected_dip_inr": forecast_data.get("min_projected_balance_inr"),
        "minimum_projected_date": forecast_data.get("shortfall_date") or "Near month-end",
        "shortfall_detected": forecast_data.get("shortfall_detected", False),
        "shortfall_risk_level": risk_info.get("risk_level", "SAFE"),
        "shortfall_probability_pct": risk_info.get("shortfall_probability_pct", 0),
        "reserve_threshold_inr": risk_info.get("reserve_threshold_inr", 10000.0),
        "primary_negative_drivers": [d.get("description") for d in explanation.get("negative_drivers", [])],
        "primary_positive_drivers": [d.get("description") for d in explanation.get("positive_drivers", [])],
        "summary_narrative": explanation.get("summary_narrative", ""),
    }

# ============================================================================
# Tool 6: Simulate Financial Scenario
# ============================================================================

class SimulateScenarioInput(BaseModel):
    scenario_type: str = Field(..., description="Scenario type: 'AFFORD_PURCHASE', 'REDUCE_SPENDING', or 'FUTURE_SAVINGS'")
    purchase_amount_inr: Optional[float] = Field(None, description="Amount for purchase affordability simulation (e.g. 15000)")
    reserve_threshold_inr: Optional[float] = Field(10000.0, description="Safety reserve threshold in INR. Defaults to 10000.")
    target_reduction_inr: Optional[float] = Field(None, description="Target monthly expenditure reduction amount (e.g. 2000)")
    target_months: Optional[int] = Field(6, description="Timeline horizon in months for savings projection (e.g. 6)")
    monthly_savings_boost_inr: Optional[float] = Field(None, description="Hypothetical additional monthly savings (e.g. 3000)")

def execute_simulate_scenario(db: Session, user_id: uuid.UUID, params: SimulateScenarioInput) -> Dict[str, Any]:
    # 1. Fetch live metrics
    summary = get_dashboard_summary(db, user_id, period="current_month")
    liquid_inr = summary.total_liquid_balance_inr
    income_inr = summary.total_income_inr
    expenses_inr = summary.total_expenses_inr
    savings_inr = summary.net_savings_inr
    savings_rate = summary.savings_rate

    sc_type = params.scenario_type.upper()

    if sc_type == "AFFORD_PURCHASE":
        purchase_amt = params.purchase_amount_inr or 15000.0
        reserve_thresh = params.reserve_threshold_inr or 10000.0

        # Retrieve cash-flow forecast minimum dip point
        fc = generate_forecast_service(db, user_id, horizon_days=30, model_type="auto", reserve_threshold_inr=reserve_thresh)
        min_dip_inr = fc.get("min_projected_balance_inr", liquid_inr)
        post_purchase_dip = min_dip_inr - purchase_amt
        post_purchase_liquid = liquid_inr - purchase_amt

        if post_purchase_dip >= reserve_thresh:
            verdict = "AFFORDABLE_SAFE"
            verdict_text = "Affordable without breaching your emergency reserve"
            recommendation = (
                f"You can safely afford this ₹{purchase_amt:,.0f} purchase. Even after deducting ₹{purchase_amt:,.0f}, "
                f"your projected minimum liquid cash cushion remains ₹{post_purchase_dip:,.2f}, safely preserving "
                f"your ₹{reserve_thresh:,.0f} emergency reserve target."
            )
        elif post_purchase_liquid >= reserve_thresh:
            verdict = "TEMPORARY_DIP_WARNING"
            verdict_text = "Affordable from current balance, but creates a temporary pre-salary buffer deficit"
            recommendation = (
                f"You have sufficient immediate cash (₹{liquid_inr:,.2f}), but spending ₹{purchase_amt:,.0f} now would cause "
                f"your projected dip balance before the next salary to drop to ₹{post_purchase_dip:,.2f}, below your ₹{reserve_thresh:,.0f} safety reserve. "
                f"Recommendation: Postpone the purchase by 1-2 weeks until after your salary credit, or split via 3-month no-cost EMI."
            )
        else:
            verdict = "NOT_RECOMMENDED_DEFICIT"
            verdict_text = "Not recommended: causes immediate emergency reserve breach"
            recommendation = (
                f"Spending ₹{purchase_amt:,.0f} will immediately compromise your emergency liquidity, leaving only ₹{post_purchase_liquid:,.2f} "
                f"against your ₹{reserve_thresh:,.0f} safety threshold. Suggest saving ₹{purchase_amt/3:,.0f}/month across the next 3 months instead."
            )

        return {
            "scenario": "AFFORD_PURCHASE",
            "purchase_amount_inr": purchase_amt,
            "reserve_threshold_inr": reserve_thresh,
            "current_liquid_inr": liquid_inr,
            "current_monthly_surplus_inr": savings_inr,
            "projected_pre_purchase_min_dip_inr": min_dip_inr,
            "projected_post_purchase_min_dip_inr": round(post_purchase_dip, 2),
            "verdict": verdict,
            "verdict_title": verdict_text,
            "recommendation": recommendation,
        }

    elif sc_type == "REDUCE_SPENDING":
        target_cut = params.target_reduction_inr or 2000.0
        cat_breakdown = get_category_breakdown(db, user_id, period="current_month")

        # Discretionary categories for reduction
        discretionary_candidates = []
        for c in cat_breakdown:
            name_lower = c.category_name.lower()
            if any(k in name_lower for k in ["food", "dining", "shopping", "entertainment", "apparel", "cafe", "online"]):
                discretionary_candidates.append(c)

        reduction_plan = []
        remaining_target = target_cut

        for c in discretionary_candidates:
            if remaining_target <= 0:
                break
            # Suggest cutting up to 20% of current spend or remaining target
            suggested_cut = min(c.spent_inr * 0.20, remaining_target)
            if suggested_cut >= 200:
                suggested_cut = round(suggested_cut, 0)
                reduction_plan.append({
                    "category_name": c.category_name,
                    "current_spent_inr": c.spent_inr,
                    "recommended_cut_inr": suggested_cut,
                    "target_spent_inr": round(c.spent_inr - suggested_cut, 0),
                    "action_tip": f"Limit non-essential delivery or impulse orders by 1-2 orders this month.",
                })
                remaining_target -= suggested_cut

        # If target cut not fully allocated, distribute evenly across Food and Shopping
        if remaining_target > 0 and reduction_plan:
            reduction_plan[0]["recommended_cut_inr"] += remaining_target
            reduction_plan[0]["target_spent_inr"] -= remaining_target

        achieved_cut = sum(r["recommended_cut_inr"] for r in reduction_plan)

        return {
            "scenario": "REDUCE_SPENDING",
            "target_reduction_inr": target_cut,
            "achieved_reduction_inr": achieved_cut,
            "projected_monthly_savings_inr": round(savings_inr + achieved_cut, 2),
            "projected_savings_rate_pct": round(((savings_inr + achieved_cut) / income_inr) * 100.0, 1) if income_inr > 0 else 0.0,
            "recommended_allocation": reduction_plan,
        }

    elif sc_type == "FUTURE_SAVINGS":
        months = params.target_months or 6
        monthly_boost = params.monthly_savings_boost_inr or 3000.0

        baseline_monthly_savings = max(0.0, savings_inr)
        optimized_monthly_savings = baseline_monthly_savings + monthly_boost

        baseline_cumulative = round(baseline_monthly_savings * months, 2)
        optimized_cumulative = round(optimized_monthly_savings * months, 2)
        wealth_delta = round(optimized_cumulative - baseline_cumulative, 2)

        monthly_progression = [
            {
                "month_index": m,
                "month_label": f"Month {m}",
                "baseline_savings_inr": round(baseline_monthly_savings * m, 2),
                "optimized_savings_inr": round(optimized_monthly_savings * m, 2),
                "wealth_differential_inr": round((optimized_monthly_savings - baseline_monthly_savings) * m, 2),
            }
            for m in range(1, months + 1)
        ]

        return {
            "scenario": "FUTURE_SAVINGS",
            "target_months": months,
            "baseline_monthly_savings_inr": baseline_monthly_savings,
            "monthly_savings_boost_inr": monthly_boost,
            "optimized_monthly_savings_inr": optimized_monthly_savings,
            "baseline_cumulative_savings_inr": baseline_cumulative,
            "optimized_cumulative_savings_inr": optimized_cumulative,
            "total_wealth_created_inr": wealth_delta,
            "monthly_progression": monthly_progression,
        }

    else:
        return {"error": f"Unknown scenario_type: {params.scenario_type}"}

# ============================================================================
# Tool 7: Financial Health Score
# ============================================================================

class GetHealthScoreInput(BaseModel):
    pass

def execute_get_financial_health_score(db: Session, user_id: uuid.UUID, params: GetHealthScoreInput) -> Dict[str, Any]:
    from app.services.planning_service import calculate_financial_health_score
    res = calculate_financial_health_score(db, user_id)
    return res.model_dump()

# ============================================================================
# Tool 8: Personalized Recommendations
# ============================================================================

class GetRecommendationsInput(BaseModel):
    status: Optional[str] = "all"

def execute_get_personalized_recommendations(db: Session, user_id: uuid.UUID, params: GetRecommendationsInput) -> Dict[str, Any]:
    from app.services.recommendation_service import generate_personalized_recommendations
    recs = generate_personalized_recommendations(db, user_id)
    return {"recommendations": [r.model_dump() for r in recs]}

# ============================================================================
# Tool Registry Specifications for Function Calling
# ============================================================================

AVAILABLE_TOOLS_SPEC = [
    {
        "type": "function",
        "function": {
            "name": "query_aggregate_transactions",
            "description": "Query aggregate spending, debits, or credits by category, date range, or merchant.",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "ISO start date YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "ISO end date YYYY-MM-DD"},
                    "category_slug": {"type": "string", "description": "Category name or slug like 'food-dining', 'groceries', 'transport', 'shopping'"},
                    "transaction_type": {"type": "string", "enum": ["DEBIT", "CREDIT", "ALL"]},
                    "merchant_keyword": {"type": "string", "description": "Merchant name filter like 'Swiggy', 'Amazon'"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compare_time_periods",
            "description": "Compare spending across time periods (e.g. this month vs last month) to detect categories that increased the most.",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_type": {"type": "string", "enum": ["month_over_month", "custom"]},
                    "p1_start": {"type": "string"},
                    "p1_end": {"type": "string"},
                    "p2_start": {"type": "string"},
                    "p2_end": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_recurring_payments",
            "description": "Retrieve user's active recurring obligations (bills, rent, EMI, subscriptions, salary) due soon.",
            "parameters": {
                "type": "object",
                "properties": {
                    "due_within_days": {"type": "integer", "description": "Number of upcoming days to inspect (default 30)"},
                    "transaction_type": {"type": "string", "enum": ["DEBIT", "CREDIT"]},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_and_goals_progress",
            "description": "Read monthly budget limits, current category utilization, pacing status, and active savings goals.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_goals": {"type": "boolean", "default": True},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_cashflow_forecast",
            "description": "Retrieve cash-flow projections, predicted month-end balance, minimum dip points, and shortfall risk.",
            "parameters": {
                "type": "object",
                "properties": {
                    "horizon_days": {"type": "integer", "default": 30},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "simulate_financial_scenario",
            "description": "Run deterministic financial simulations: purchase affordability check, spending cut allocation, or 6-month savings projection.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_type": {"type": "string", "enum": ["AFFORD_PURCHASE", "REDUCE_SPENDING", "FUTURE_SAVINGS"]},
                    "purchase_amount_inr": {"type": "number", "description": "Purchase amount in INR for affordability check"},
                    "reserve_threshold_inr": {"type": "number", "description": "Emergency reserve threshold (default 10000)"},
                    "target_reduction_inr": {"type": "number", "description": "Target monthly spending cut in INR (e.g. 2000)"},
                    "target_months": {"type": "integer", "description": "Months horizon for savings projection (default 6)"},
                    "monthly_savings_boost_inr": {"type": "number", "description": "Monthly savings increase in INR"},
                },
                "required": ["scenario_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_financial_health_score",
            "description": "Calculate explainable 0-100 financial health score, sub-scores, factor breakdown, and actionable improvements.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_personalized_recommendations",
            "description": "Retrieve prioritized personalized financial recommendations for budget cuts, subscriptions, and emergency reserves.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "enum": ["new", "accepted", "dismissed", "completed", "all"], "default": "all"}
                },
            },
        },
    },
]
