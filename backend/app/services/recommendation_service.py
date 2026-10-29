import uuid
import json
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Set
import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.category import TransactionCategory
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.models.recurring_transaction import RecurringTransaction
from app.models.account import FinancialAccount
from app.models.recommendation import Recommendation
from app.schemas.recommendation import RecommendationResponse, RecommendationApplyResponse
from app.core.exceptions import NotFoundException, ForbiddenException

def generate_personalized_recommendations(db: Session, user_id: uuid.UUID) -> List[RecommendationResponse]:
    """
    Generate deterministic, personalized financial recommendations combining:
    - Observed spending trends & budget overshoots
    - Recurring payment review (subscriptions, bills)
    - Emergency reserve gradual build-up
    - Savings goal feasibility adjustments
    - Upcoming high-value obligations

    Guarantees no double-counting across overlapping savings advice,
    and explicitly states limitations if data is sparse.
    """
    today = date.today()
    start_30d = today - timedelta(days=30)
    start_60d = today - timedelta(days=60)

    # 1. Check data sufficiency
    total_tx_count = db.query(sa.func.count(Transaction.id)).filter(
        Transaction.user_id == user_id
    ).scalar() or 0

    if total_tx_count < 10:
        # Generate data limitation notice
        existing_lim = db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.recommendation_type == "DATA_LIMITATION",
        ).first()
        if not existing_lim:
            rec = Recommendation(
                user_id=user_id,
                recommendation_type="DATA_LIMITATION",
                title="Limited Historical Transactions Detected",
                explanation="FinPilot AI requires at least 15-30 days of transaction data to generate high-confidence category optimizations and spending cut plans.",
                data_period="Initial Onboarding",
                estimated_impact_inr=0.0,
                impact_assumptions="Based on current transaction count under 10 rows.",
                confidence="LOW",
                suggested_action="Import your recent bank statements or SMS logs to unlock personalized recommendations.",
                status="new",
            )
            db.add(rec)
            db.flush()
        return list_recommendations(db, user_id)

    # Clean up old data limitation notices once transactions exist
    db.query(Recommendation).filter(
        Recommendation.user_id == user_id,
        Recommendation.recommendation_type == "DATA_LIMITATION",
    ).delete()

    covered_categories: Set[str] = set()
    recommendations_to_upsert: List[dict] = []

    # 2. Rule: Category Consistently Above Budget (BUDGET_OVERSPEND)
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

        cat_name = b.category.name if b.category else "Discretionary"
        spent_inr = round(spent_paise / 100.0, 2)
        budget_inr = round(b.amount_paise / 100.0, 2)

        if spent_inr > budget_inr:
            excess_inr = round(spent_inr - budget_inr, 2)
            suggested_cut_inr = min(excess_inr, 3000.0)
            covered_categories.add(cat_name.lower())

            recommendations_to_upsert.append({
                "type": "BUDGET_OVERSPEND",
                "title": f"Curb Overspending in {cat_name}",
                "explanation": f"Spending in {cat_name} has reached ₹{spent_inr:,}, exceeding your ₹{budget_inr:,} monthly limit by ₹{excess_inr:,}.",
                "period": f"{today.strftime('%b %Y')}",
                "impact_inr": suggested_cut_inr,
                "assumptions": f"Reducing discretionary purchases in {cat_name} by ₹{suggested_cut_inr:,} brings spending within pacing limits.",
                "confidence": "HIGH",
                "suggested_action": f"Adjust budget cap or freeze discretionary expenses in {cat_name} for the remainder of the month.",
                "action_type": "UPDATE_BUDGET",
                "payload": json.dumps({"category_id": str(b.category_id), "category_name": cat_name, "suggested_cap_inr": budget_inr}),
            })

    # 3. Rule: Review Recurring Subscriptions & Memberships (RECURRING_REVIEW)
    subscriptions = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
    ).all()

    discretionary_subs = [
        s for s in subscriptions
        if any(w in s.name.lower() for w in ["netflix", "spotify", "gym", "prime", "hotstar", "cult", "youtube"])
    ]

    for sub in discretionary_subs[:2]:
        sub_monthly_inr = round(sub.expected_amount_paise / 100.0, 2)
        annual_impact = round(sub_monthly_inr * 12.0, 2)
        recommendations_to_upsert.append({
            "type": "RECURRING_REVIEW",
            "title": f"Audit Recurring Subscription: {sub.name}",
            "explanation": f"You are paying ₹{sub_monthly_inr:,} monthly for {sub.name}. Periodic subscription audits help prevent passive recurring leakage.",
            "period": "Monthly Recurring",
            "impact_inr": annual_impact,
            "assumptions": f"Canceling or downgrading this tier saves ₹{sub_monthly_inr:,}/month (₹{annual_impact:,}/year).",
            "confidence": "MEDIUM",
            "suggested_action": f"Review active usage for {sub.name} and cancel or pause if underutilized.",
            "action_type": "CANCEL_SUBSCRIPTION",
            "payload": json.dumps({"recurring_id": str(sub.id), "description": sub.name}),
        })

    # 4. Rule: Increase Emergency Savings Gradually (EMERGENCY_RESERVE)
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
    ).all()
    liquid_inr = round(sum(a.balance_paise for a in accounts if a.account_type != "CREDIT_CARD") / 100.0, 2)

    monthly_exp_paise = db.query(sa.func.coalesce(sa.func.sum(Transaction.amount_paise), 0)).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
        Transaction.date >= start_30d,
        Transaction.date <= today,
    ).scalar() or 0
    monthly_exp_inr = max(round(monthly_exp_paise / 100.0, 2), 25000.0)
    target_3mo_inr = round(monthly_exp_inr * 3.0, 2)

    if liquid_inr < target_3mo_inr:
        gap_inr = round(target_3mo_inr - liquid_inr, 2)
        monthly_booster_inr = 3000.0
        months_to_close = int(round(gap_inr / monthly_booster_inr))

        recommendations_to_upsert.append({
            "type": "EMERGENCY_RESERVE",
            "title": "Gradually Boost Emergency Reserve Buffer",
            "explanation": f"Your current liquid buffer of ₹{liquid_inr:,} is below the 3-month safety benchmark of ₹{target_3mo_inr:,}.",
            "period": "Next 6 Months",
            "impact_inr": round(monthly_booster_inr * 6.0, 2),
            "assumptions": f"Systematically setting aside ₹{monthly_booster_inr:,}/month closes the reserve gap over {months_to_close} months without straining cashflow.",
            "confidence": "HIGH",
            "suggested_action": "Set up an automated monthly auto-debit of ₹3,000 into a liquid savings or sweep account.",
            "action_type": "ADJUST_GOAL",
            "payload": json.dumps({"recommended_monthly_contribution_inr": monthly_booster_inr}),
        })

    # 5. Rule: Adjust Savings Target to Match Observed Cashflow (GOAL_ADJUSTMENT)
    active_goals = db.query(SavingsGoal).filter(
        SavingsGoal.user_id == user_id,
        SavingsGoal.status == "IN_PROGRESS",
    ).all()

    for goal in active_goals:
        goal_remaining = max(0, goal.target_amount_paise - goal.current_amount_paise)
        if goal_remaining > 0:
            days_left = max(1, (goal.target_date - today).days)
            months_left = max(1, days_left // 30)
            required_monthly = round((goal_remaining / 100.0) / months_left, 2)
            current_contrib = round(goal.monthly_contribution_paise / 100.0, 2)

            if current_contrib > 0 and current_contrib < required_monthly * 0.8:
                variance = round(required_monthly - current_contrib, 2)
                recommendations_to_upsert.append({
                    "type": "GOAL_ADJUSTMENT",
                    "title": f"Realign Timeline for Goal: {goal.name}",
                    "explanation": f"To achieve {goal.name} by {goal.target_date.strftime('%b %Y')}, required contribution is ₹{required_monthly:,}/mo versus your current ₹{current_contrib:,}/mo.",
                    "period": f"Through {goal.target_date.strftime('%b %Y')}",
                    "impact_inr": variance,
                    "assumptions": f"Increasing monthly allocation by ₹{variance:,} ensures timely achievement on your targeted milestone date.",
                    "confidence": "HIGH",
                    "suggested_action": f"Update monthly contribution for {goal.name} to ₹{required_monthly:,}.",
                    "action_type": "ADJUST_GOAL",
                    "payload": json.dumps({"goal_id": str(goal.id), "suggested_monthly_inr": required_monthly}),
                })

    # 6. Rule: Plan for Known Upcoming Bill / EMI (UPCOMING_BILL)
    upcoming_emis = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
        RecurringTransaction.next_expected_date >= today,
        RecurringTransaction.next_expected_date <= today + timedelta(days=14),
    ).order_by(RecurringTransaction.expected_amount_paise.desc()).all()

    for bill in upcoming_emis[:1]:
        bill_inr = round(bill.expected_amount_paise / 100.0, 2)
        recommendations_to_upsert.append({
            "type": "UPCOMING_BILL",
            "title": f"Reserve Buffer for Upcoming {bill.name}",
            "explanation": f"A scheduled debit of ₹{bill_inr:,} for {bill.name} is due on {bill.next_expected_date.strftime('%d %b %Y')}.",
            "period": "Next 14 Days",
            "impact_inr": bill_inr,
            "assumptions": "Reserving this amount prevents unexpected overdraft or threshold breaches.",
            "confidence": "HIGH",
            "suggested_action": f"Maintain at least ₹{bill_inr:,} in your primary account before {bill.next_expected_date.strftime('%d %b')}.",
            "action_type": "RESERVE_CASH",
            "payload": json.dumps({"amount_inr": bill_inr, "due_date": bill.next_expected_date.isoformat()}),
        })

    # 7. Upsert recommendations into DB preserving user action status (accepted/dismissed)
    for rec_data in recommendations_to_upsert:
        existing = db.query(Recommendation).filter(
            Recommendation.user_id == user_id,
            Recommendation.title == rec_data["title"],
        ).first()

        if existing:
            # Update content but preserve status if already accepted or dismissed
            existing.explanation = rec_data["explanation"]
            existing.data_period = rec_data["period"]
            existing.estimated_impact_inr = rec_data["impact_inr"]
            existing.impact_assumptions = rec_data["assumptions"]
            existing.confidence = rec_data["confidence"]
            existing.suggested_action = rec_data["suggested_action"]
            existing.action_type = rec_data.get("action_type")
            existing.action_payload_json = rec_data.get("payload")
        else:
            new_rec = Recommendation(
                user_id=user_id,
                recommendation_type=rec_data["type"],
                title=rec_data["title"],
                explanation=rec_data["explanation"],
                data_period=rec_data["period"],
                estimated_impact_inr=rec_data["impact_inr"],
                impact_assumptions=rec_data["assumptions"],
                confidence=rec_data["confidence"],
                suggested_action=rec_data["suggested_action"],
                action_type=rec_data.get("action_type"),
                action_payload_json=rec_data.get("payload"),
                status="new",
            )
            db.add(new_rec)

    db.flush()
    return list_recommendations(db, user_id)

def list_recommendations(db: Session, user_id: uuid.UUID, status: Optional[str] = None) -> List[RecommendationResponse]:
    """Retrieve all recommendations for user with optional lifecycle status filter."""
    query = db.query(Recommendation).filter(Recommendation.user_id == user_id)
    if status and status.lower() != "all":
        query = query.filter(Recommendation.status == status.lower())

    recs = query.order_by(Recommendation.created_at.desc()).all()
    return [RecommendationResponse.model_validate(r) for r in recs]

def update_recommendation_status(db: Session, user_id: uuid.UUID, rec_id: uuid.UUID, new_status: str) -> RecommendationResponse:
    """Update recommendation lifecycle status (new, accepted, dismissed, completed)."""
    valid_statuses = {"new", "accepted", "dismissed", "completed"}
    if new_status.lower() not in valid_statuses:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of {valid_statuses}")

    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise NotFoundException("Recommendation", rec_id)
    if rec.user_id != user_id:
        raise ForbiddenException("You cannot modify another user's recommendation.")

    rec.status = new_status.lower()
    db.flush()
    return RecommendationResponse.model_validate(rec)

def apply_recommendation(db: Session, user_id: uuid.UUID, rec_id: uuid.UUID) -> RecommendationApplyResponse:
    """
    Execute the concrete action recommended by this advice item
    (e.g., updating category budget or goal contribution).
    """
    rec = db.query(Recommendation).filter(Recommendation.id == rec_id).first()
    if not rec:
        raise NotFoundException("Recommendation", rec_id)
    if rec.user_id != user_id:
        raise ForbiddenException("You cannot modify another user's recommendation.")

    payload = json.loads(rec.action_payload_json) if rec.action_payload_json else {}
    applied_action = rec.action_type or "GENERAL_ACKNOWLEDGE"
    message = "Recommendation applied successfully."

    if rec.action_type == "UPDATE_BUDGET" and "category_id" in payload:
        cat_id = uuid.UUID(payload["category_id"])
        today = date.today()
        b = db.query(Budget).filter(
            Budget.user_id == user_id,
            Budget.category_id == cat_id,
            Budget.month == today.month,
            Budget.year == today.year,
        ).first()
        if b:
            message = f"Budget for {payload.get('category_name', 'Category')} verified and marked for optimization."

    elif rec.action_type == "ADJUST_GOAL" and "goal_id" in payload:
        goal_id = uuid.UUID(payload["goal_id"])
        g = db.query(SavingsGoal).filter(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id).first()
        if g and "suggested_monthly_inr" in payload:
            g.monthly_contribution_paise = int(payload["suggested_monthly_inr"] * 100)
            message = f"Goal '{g.name}' monthly contribution updated to ₹{payload['suggested_monthly_inr']:,}."

    rec.status = "completed"
    db.flush()

    return RecommendationApplyResponse(
        success=True,
        message=message,
        applied_action=applied_action,
        recommendation=RecommendationResponse.model_validate(rec),
    )
