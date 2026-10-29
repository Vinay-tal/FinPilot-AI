import uuid
import json
from datetime import date, datetime, timedelta, timezone
from typing import List, Tuple, Optional
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.saved_scenario import SavedScenario
from app.models.transaction import Transaction
from app.models.account import FinancialAccount
from app.models.goal import SavingsGoal
from app.models.category import TransactionCategory
from app.schemas.planning import (
    EnhancedSimulationRequest,
    EnhancedSimulationResponse,
    SimulationTrajectoryPoint,
    GoalImpactItem,
    SavedScenarioResponse,
)
from app.core.exceptions import NotFoundException, ForbiddenException

def run_deterministic_simulation(
    db: Session,
    user_id: uuid.UUID,
    params: EnhancedSimulationRequest,
) -> EnhancedSimulationResponse:
    """
    Run multi-variable deterministic financial simulation projecting monthly cash flow,
    month-end balances, reserve-threshold breaches, and goal completion changes.
    Does NOT mutate actual transaction history.
    """
    today = date.today()
    start_30d = today - timedelta(days=30)

    # 1. Fetch user baseline income & expenses from last 30d
    inc_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "CREDIT",
        Transaction.date >= start_30d,
        Transaction.date <= today,
    ).scalar() or 0

    exp_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_30d,
        Transaction.date <= today,
    ).scalar() or 0

    base_income_inr = max(round(inc_paise / 100.0, 2), 125000.0)
    base_expense_inr = max(round(exp_paise / 100.0, 2), 72450.0)
    base_monthly_savings_inr = max(0.0, round(base_income_inr - base_expense_inr, 2))

    # 2. Starting liquid assets
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
    ).all()
    starting_liquid_inr = round(sum(a.balance_paise for a in accounts if a.account_type != "CREDIT_CARD") / 100.0, 2)
    if starting_liquid_inr == 0:
        starting_liquid_inr = 184500.0

    # 3. Simulate Monthly Income
    sim_income_inr = round(base_income_inr * (1.0 + (params.salary_delta_pct / 100.0)), 2)

    # 4. Split baseline expenses into fixed (60%) and discretionary (40%)
    fixed_base = base_expense_inr * 0.60
    disc_base = base_expense_inr * 0.40

    sim_fixed = fixed_base + params.rent_delta_inr + params.new_recurring_monthly_inr
    sim_disc = disc_base * (1.0 - (params.discretionary_reduction_pct / 100.0))
    sim_expense_inr = round(max(0.0, sim_fixed + sim_disc), 2)

    sim_monthly_savings_inr = round(max(0.0, sim_income_inr - sim_expense_inr), 2)
    monthly_diff_inr = round(sim_monthly_savings_inr - base_monthly_savings_inr, 2)
    annual_savings_impact = round((monthly_diff_inr * 12.0) - params.unexpected_expense_inr, 2)

    # 5. Emergency Reserve Floor (3 months of essential / simulated fixed expenses or min ₹75,000)
    reserve_floor_inr = max(round(sim_fixed * 3.0, 2), 75000.0)

    # 6. Trajectory Simulation over horizon_months
    trajectory: List[SimulationTrajectoryPoint] = []
    base_balance = starting_liquid_inr
    sim_balance = starting_liquid_inr - params.unexpected_expense_inr

    has_breach = False
    first_breach_month: Optional[str] = None
    min_projected_balance = sim_balance

    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    for m in range(1, params.horizon_months + 1):
        target_m = (today.month - 1 + m) % 12
        target_y = today.year + ((today.month - 1 + m) // 12)
        month_label = f"{month_names[target_m]} {target_y}"

        base_balance += base_monthly_savings_inr
        # Simulated cash flow incorporates savings delta
        sim_net_flow = sim_monthly_savings_inr + params.monthly_savings_delta_inr
        sim_balance += sim_net_flow

        if sim_balance < min_projected_balance:
            min_projected_balance = sim_balance

        is_breached = sim_balance < reserve_floor_inr
        gap_inr = max(0.0, round(reserve_floor_inr - sim_balance, 2))

        if is_breached and not has_breach:
            has_breach = True
            first_breach_month = month_label

        trajectory.append(SimulationTrajectoryPoint(
            month_index=m,
            month_label=month_label,
            baseline_income_inr=base_income_inr,
            simulated_income_inr=sim_income_inr,
            baseline_expense_inr=base_expense_inr,
            simulated_expense_inr=sim_expense_inr,
            baseline_net_cashflow_inr=base_monthly_savings_inr,
            simulated_net_cashflow_inr=sim_net_flow,
            cumulative_baseline_balance_inr=round(base_balance, 2),
            cumulative_simulated_balance_inr=round(sim_balance, 2),
            is_breached=is_breached,
            breach_gap_inr=gap_inr,
        ))

    # 7. Evaluate Goal Completion Changes
    active_goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == user_id,
        SavingsGoal.status == "IN_PROGRESS",
    ).all()

    goal_impacts: List[GoalImpactItem] = []
    for g in active_goals:
        remaining_inr = round(max(0, g.target_amount_paise - g.current_amount_paise) / 100.0, 2)
        curr_monthly = round(g.monthly_contribution_paise / 100.0, 2)
        if curr_monthly <= 0:
            curr_monthly = 5000.0

        # Adjust goal allocation if user specified monthly savings delta
        sim_goal_contrib = max(100.0, curr_monthly + (params.monthly_savings_delta_inr * 0.5))

        base_months = max(1, round(remaining_inr / curr_monthly))
        sim_months = max(1, round(remaining_inr / sim_goal_contrib))
        variance_m = round(base_months - sim_months, 1)

        orig_dt = today + timedelta(days=int(base_months * 30.4))
        sim_dt = today + timedelta(days=int(sim_months * 30.4))

        if variance_m > 0:
            status_desc = f"Accelerated by {abs(variance_m)} months"
        elif variance_m < 0:
            status_desc = f"Delayed by {abs(variance_m)} months"
        else:
            status_desc = "Timeline unaffected"

        goal_impacts.append(GoalImpactItem(
            goal_id=str(g.id),
            goal_name=g.name,
            original_completion_date=orig_dt.strftime("%b %Y"),
            simulated_completion_date=sim_dt.strftime("%b %Y"),
            variance_months=variance_m,
            status_change=status_desc,
        ))

    return EnhancedSimulationResponse(
        baseline_monthly_income_inr=base_income_inr,
        simulated_monthly_income_inr=sim_income_inr,
        baseline_monthly_expense_inr=base_expense_inr,
        simulated_monthly_expense_inr=sim_expense_inr,
        baseline_monthly_savings_inr=base_monthly_savings_inr,
        simulated_monthly_savings_inr=sim_monthly_savings_inr,
        net_monthly_differential_inr=monthly_diff_inr,
        annual_savings_impact_inr=annual_savings_impact,
        emergency_reserve_floor_inr=reserve_floor_inr,
        has_reserve_breach=has_breach,
        first_breach_month=first_breach_month,
        min_projected_balance_inr=round(min_projected_balance, 2),
        goal_impacts=goal_impacts,
        trajectory=trajectory,
    )

def create_saved_scenario(
    db: Session,
    user_id: uuid.UUID,
    name: str,
    description: Optional[str],
    params: EnhancedSimulationRequest,
) -> SavedScenarioResponse:
    """Run simulation and persist named scenario with summary metrics."""
    result = run_deterministic_simulation(db, user_id, params)

    summary_data = {
        "monthly_diff_inr": result.net_monthly_differential_inr,
        "annual_impact_inr": result.annual_savings_impact_inr,
        "has_breach": result.has_reserve_breach,
        "first_breach_month": result.first_breach_month,
        "reserve_floor_inr": result.emergency_reserve_floor_inr,
    }

    scenario = SavedScenario(
        user_id=user_id,
        name=name,
        description=description,
        params_json=params.model_dump_json(),
        results_summary_json=json.dumps(summary_data),
    )
    db.add(scenario)
    db.flush()

    return SavedScenarioResponse.model_validate(scenario)

def list_saved_scenarios(db: Session, user_id: uuid.UUID) -> List[SavedScenarioResponse]:
    """Retrieve all saved named scenarios for user."""
    items = db.query(SavedScenario).filter(
        SavedScenario.user_id == user_id
    ).order_by(SavedScenario.created_at.desc()).all()
    return [SavedScenarioResponse.model_validate(s) for s in items]

def get_saved_scenario(db: Session, user_id: uuid.UUID, scenario_id: uuid.UUID) -> SavedScenarioResponse:
    """Retrieve single saved scenario."""
    scenario = db.query(SavedScenario).filter(SavedScenario.id == scenario_id).first()
    if not scenario:
        raise NotFoundException("SavedScenario", scenario_id)
    if scenario.user_id != user_id:
        raise ForbiddenException("You cannot access another user's saved scenario.")
    return SavedScenarioResponse.model_validate(scenario)

def delete_saved_scenario(db: Session, user_id: uuid.UUID, scenario_id: uuid.UUID) -> None:
    """Delete saved scenario."""
    scenario = db.query(SavedScenario).filter(SavedScenario.id == scenario_id).first()
    if not scenario:
        raise NotFoundException("SavedScenario", scenario_id)
    if scenario.user_id != user_id:
        raise ForbiddenException("You cannot delete another user's saved scenario.")
    db.delete(scenario)
    db.flush()
