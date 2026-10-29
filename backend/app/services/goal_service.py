import uuid
from datetime import date, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.goal import SavingsGoal
from app.models.transaction import Transaction
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse, GoalSimulationResponse
from app.core.exceptions import NotFoundException, ForbiddenException
import sqlalchemy as sa

def compute_goal_feasibility(goal: SavingsGoal, user_surplus_inr: float = 35000.0) -> Tuple[float, date, bool, str, float, str | None]:
    """
    Compute required monthly savings, projected completion date, feasibility status,
    and variance relative to target date.
    """
    today = date.today()
    remaining_paise = max(0, goal.target_amount_paise - goal.current_amount_paise)
    remaining_inr = round(remaining_paise / 100.0, 2)

    if remaining_inr <= 0:
        return 0.0, today, True, "COMPLETED", 0.0, None

    # Calculate months until target date
    days_until_target = max(1, (goal.target_date - today).days)
    months_until_target = max(1, round(days_until_target / 30.4))

    required_monthly_inr = round(remaining_inr / months_until_target, 2)

    # Active committed monthly contribution
    committed_monthly_inr = round(goal.monthly_contribution_paise / 100.0, 2)
    effective_monthly_inr = committed_monthly_inr if committed_monthly_inr > 0 else required_monthly_inr

    # Projected months to completion at effective rate
    months_needed = max(1, round(remaining_inr / max(effective_monthly_inr, 100.0)))
    projected_date = today + timedelta(days=int(months_needed * 30.4))

    # Variance in months (positive = completed earlier, negative = delayed)
    variance_months = round(months_until_target - months_needed, 1)

    # Feasibility
    warning: str | None = None
    if committed_monthly_inr > user_surplus_inr:
        warning = f"Monthly contribution (₹{committed_monthly_inr:,}) exceeds estimated net surplus (₹{user_surplus_inr:,})."

    if goal.status == "COMPLETED":
        status = "COMPLETED"
        is_achievable = True
    elif effective_monthly_inr >= required_monthly_inr:
        status = "ON_TRACK"
        is_achievable = True
    elif effective_monthly_inr >= required_monthly_inr * 0.75:
        status = "BEHIND"
        is_achievable = True
    else:
        status = "AT_RISK"
        is_achievable = False

    return required_monthly_inr, projected_date, is_achievable, status, variance_months, warning

def enrich_goal_response(goal: SavingsGoal, user_surplus_inr: float = 35000.0) -> GoalResponse:
    req_inr, proj_dt, achievable, stat, var_m, warn = compute_goal_feasibility(goal, user_surplus_inr)
    res = GoalResponse.model_validate(goal)
    res.required_monthly_inr = req_inr
    res.projected_completion_date = proj_dt
    res.is_achievable = achievable
    res.feasibility_status = stat
    res.variance_months = var_m
    res.cashflow_strain_warning = warn
    return res

def list_goals(db: Session, user_id: uuid.UUID) -> List[GoalResponse]:
    """Retrieve all savings goals for the authenticated user with real-time feasibility."""
    # Estimate monthly surplus from recent 30d
    today = date.today()
    inc = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "CREDIT",
        Transaction.date >= today - timedelta(days=30),
    ).scalar() or 0
    exp = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= today - timedelta(days=30),
    ).scalar() or 0
    surplus_inr = max(round((inc - exp) / 100.0, 2), 25000.0)

    goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == user_id
    ).order_by(SavingsGoal.target_date.asc()).all()

    return [enrich_goal_response(g, surplus_inr) for g in goals]

def get_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> GoalResponse:
    """Retrieve single goal with user verification and feasibility metrics."""
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not goal:
        raise NotFoundException("SavingsGoal", goal_id)
    if goal.user_id != user_id:
        raise ForbiddenException("You cannot access another user's goal.")
    return enrich_goal_response(goal)

def create_goal(db: Session, user_id: uuid.UUID, g_in: GoalCreate) -> GoalResponse:
    """Create a new savings goal."""
    goal = SavingsGoal(
        user_id=user_id,
        name=g_in.name,
        target_amount_paise=g_in.target_amount_paise,
        current_amount_paise=g_in.current_amount_paise,
        target_date=g_in.target_date,
        monthly_contribution_paise=g_in.monthly_contribution_paise,
        category=g_in.category.upper(),
        priority=g_in.priority.upper(),
        status=g_in.status.upper(),
    )
    db.add(goal)
    db.flush()
    return enrich_goal_response(goal)

def update_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, g_in: GoalUpdate) -> GoalResponse:
    """Update goal progress or attributes."""
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not goal:
        raise NotFoundException("SavingsGoal", goal_id)
    if goal.user_id != user_id:
        raise ForbiddenException("You cannot edit another user's goal.")

    update_data = g_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("category", "priority", "status") and value:
            setattr(goal, field, value.upper())
        else:
            setattr(goal, field, value)

    # Check auto-completion
    if goal.current_amount_paise >= goal.target_amount_paise and goal.status == "IN_PROGRESS":
        goal.status = "COMPLETED"

    db.flush()
    return enrich_goal_response(goal)

def delete_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    """Delete a savings goal."""
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not goal:
        raise NotFoundException("SavingsGoal", goal_id)
    if goal.user_id != user_id:
        raise ForbiddenException("You cannot delete another user's goal.")
    db.delete(goal)
    db.flush()

def simulate_goal_contribution(
    db: Session,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    monthly_contribution_inr: float,
) -> GoalSimulationResponse:
    """
    Simulate the effect of changing monthly savings contribution on goal completion date,
    timeline variance, and feasibility.
    """
    goal = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id).first()
    if not goal:
        raise NotFoundException("SavingsGoal", goal_id)
    if goal.user_id != user_id:
        raise ForbiddenException("You cannot simulate another user's goal.")

    today = date.today()
    remaining_inr = round(max(0, goal.target_amount_paise - goal.current_amount_paise) / 100.0, 2)
    target_inr = round(goal.target_amount_paise / 100.0, 2)
    current_inr = round(goal.current_amount_paise / 100.0, 2)

    days_until_target = max(1, (goal.target_date - today).days)
    months_until_target = max(1, round(days_until_target / 30.4))
    required_monthly_inr = round(remaining_inr / months_until_target, 2)

    # Simulated months
    sim_months = max(1, round(remaining_inr / max(monthly_contribution_inr, 100.0)))
    sim_completion_date = today + timedelta(days=int(sim_months * 30.4))
    variance_months = round(months_until_target - sim_months, 1)

    if variance_months > 0:
        message = f"Contributing ₹{monthly_contribution_inr:,}/month achieves your goal {abs(variance_months)} months ahead of target!"
        status = "ON_TRACK"
        is_achievable = True
    elif variance_months == 0:
        message = f"Contributing ₹{monthly_contribution_inr:,}/month achieves your goal right on schedule."
        status = "ON_TRACK"
        is_achievable = True
    else:
        message = f"Contributing ₹{monthly_contribution_inr:,}/month delays your goal by {abs(variance_months)} months beyond target."
        status = "BEHIND"
        is_achievable = False

    return GoalSimulationResponse(
        goal_id=goal.id,
        target_amount_inr=target_inr,
        current_amount_inr=current_inr,
        simulated_monthly_contribution_inr=monthly_contribution_inr,
        required_monthly_inr=required_monthly_inr,
        target_date=goal.target_date,
        simulated_completion_date=sim_completion_date,
        months_to_completion=sim_months,
        variance_months=variance_months,
        is_achievable=is_achievable,
        feasibility_status=status,
        message=message,
    )
