import uuid
from datetime import date, timedelta
import pytest
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.account import FinancialAccount
from app.models.category import TransactionCategory
from app.models.transaction import Transaction
from app.models.budget import Budget
from app.models.goal import SavingsGoal
from app.models.recurring_transaction import RecurringTransaction
from app.models.recommendation import Recommendation
from app.models.saved_scenario import SavedScenario
from app.services.planning_service import (
    calculate_financial_health_score,
    generate_monthly_report,
    export_monthly_report_csv,
    generate_system_alerts,
)
from app.services.recommendation_service import (
    generate_personalized_recommendations,
    list_recommendations,
    update_recommendation_status,
    apply_recommendation,
)
from app.services.goal_service import (
    list_goals,
    simulate_goal_contribution,
)
from app.services.simulation_service import (
    run_deterministic_simulation,
    create_saved_scenario,
    list_saved_scenarios,
    delete_saved_scenario,
)
from app.services.budget_service import (
    get_budget_recommendations,
    apply_budget_recommendations,
)
from app.schemas.planning import EnhancedSimulationRequest

@pytest.fixture
def planning_user(db: Session):
    """Seed an isolated user with accounts, categories, and transactions for planning tests."""
    user = User(
        email=f"planning_{uuid.uuid4().hex[:8]}@finpilot.in",
        password_hash="fake_hash",
        full_name="Planning Test User",
        currency="INR",
    )
    db.add(user)
    db.flush()

    # Liquid checking account
    acc = FinancialAccount(
        user_id=user.id,
        name="HDFC Salary Checking",
        account_type="SAVINGS",
        institution="HDFC Bank",
        balance_paise=15000000,  # ₹1,50,000
    )
    db.add(acc)

    # Categories
    cat_food = TransactionCategory(user_id=user.id, name="Food & Dining", slug="food-dining", is_system=False)
    cat_rent = TransactionCategory(user_id=user.id, name="Rent & Housing", slug="rent-housing", is_system=False)
    cat_shopping = TransactionCategory(user_id=user.id, name="Shopping", slug="shopping", is_system=False)
    cat_income = TransactionCategory(user_id=user.id, name="Income & Salary", slug="income-salary", is_system=False)
    db.add_all([cat_food, cat_rent, cat_shopping, cat_income])
    db.flush()

    today = date.today()
    # Salary credits (₹1,00,000)
    tx_sal = Transaction(
        user_id=user.id,
        account_id=acc.id,
        category_id=cat_income.id,
        amount_paise=10000000,
        transaction_type="CREDIT",
        date=today - timedelta(days=15),
        narration="Tech Corp Salary Credit",
        fingerprint=f"fp-sal-{uuid.uuid4().hex}",
    )
    # Debits: Food (₹15,000), Rent (₹25,000), Shopping (₹10,000)
    tx_food = Transaction(
        user_id=user.id,
        account_id=acc.id,
        category_id=cat_food.id,
        amount_paise=1500000,
        transaction_type="DEBIT",
        date=today - timedelta(days=10),
        merchant_name="Swiggy",
        narration="Swiggy Food Delivery",
        fingerprint=f"fp-food-{uuid.uuid4().hex}",
    )
    tx_rent = Transaction(
        user_id=user.id,
        account_id=acc.id,
        category_id=cat_rent.id,
        amount_paise=2500000,
        transaction_type="DEBIT",
        date=today - timedelta(days=20),
        merchant_name="Landlord",
        narration="Rent payment",
        fingerprint=f"fp-rent-{uuid.uuid4().hex}",
    )
    tx_shop = Transaction(
        user_id=user.id,
        account_id=acc.id,
        category_id=cat_shopping.id,
        amount_paise=1000000,
        transaction_type="DEBIT",
        date=today - timedelta(days=5),
        merchant_name="Amazon",
        narration="Amazon Shopping",
        fingerprint=f"fp-shop-{uuid.uuid4().hex}",
    )
    extra_txs = [
        Transaction(
            user_id=user.id,
            account_id=acc.id,
            category_id=cat_food.id,
            amount_paise=45000,
            transaction_type="DEBIT",
            date=today - timedelta(days=i * 2 + 1),
            merchant_name=f"Merchant {i}",
            narration=f"Daily spend {i}",
            fingerprint=f"fp-extra-{i}-{uuid.uuid4().hex}",
        )
        for i in range(1, 9)
    ]
    db.add_all([tx_sal, tx_food, tx_rent, tx_shop] + extra_txs)

    # Budget: Food limit ₹10,000 (spent ₹15,000 -> overspent!)
    b_food = Budget(
        user_id=user.id,
        category_id=cat_food.id,
        month=today.month,
        year=today.year,
        amount_paise=1000000,  # ₹10,000
        alert_threshold=0.80,
    )
    db.add(b_food)

    # Goal: Goa Trip ₹60,000 in 6 months
    goal = SavingsGoal(
        user_id=user.id,
        name="Goa Trip",
        target_amount_paise=6000000,
        current_amount_paise=1500000,
        target_date=today + timedelta(days=180),
        monthly_contribution_paise=500000,  # ₹5,000/mo
        category="VACATION",
        priority="MEDIUM",
        status="IN_PROGRESS",
    )
    db.add(goal)

    # Recurring: Netflix ₹649/mo
    rec = RecurringTransaction(
        user_id=user.id,
        category_id=cat_food.id,
        name="Netflix India Subscription",
        merchant_name="Netflix",
        expected_amount_paise=64900,
        frequency="MONTHLY",
        next_expected_date=today + timedelta(days=7),
        is_active=True,
    )
    db.add(rec)
    db.flush()

    return user

def test_financial_health_score_calculation(db: Session, planning_user: User):
    """Verify explainable 0-100 financial health score with sub-factor normalization and disclosures."""
    score = calculate_financial_health_score(db, planning_user.id)

    assert 0 <= score.overall_score <= 100
    assert score.grade in ["Excellent", "Good", "Fair", "Needs Attention"]
    assert "heuristic" in score.disclaimer.lower()
    assert len(score.factors) == 6

    # Verify factor names and structure
    factor_ids = {f.factor_id for f in score.factors}
    assert "savings_rate" in factor_ids
    assert "essential_coverage" in factor_ids
    assert "emergency_reserve" in factor_ids
    assert "budget_adherence" in factor_ids
    assert "debt_burden" in factor_ids
    assert "stability" in factor_ids

    # For planning_user with no debt accounts, debt factor should disclose exclusion or be handled gracefully
    debt_factor = next(f for f in score.factors if f.factor_id == "debt_burden")
    assert debt_factor.is_excluded or debt_factor.score >= 0

def test_personalized_recommendations_generation_and_lifecycle(db: Session, planning_user: User):
    """Verify recommendation generation, overspend detection, and lifecycle status updates."""
    recs = generate_personalized_recommendations(db, planning_user.id)
    assert len(recs) >= 1

    # Overspending in Food & Dining should have triggered a recommendation
    food_rec = next((r for r in recs if "food & dining" in r.title.lower() or "overspending" in r.title.lower()), None)
    assert food_rec is not None
    assert food_rec.status == "new"
    assert food_rec.estimated_impact_inr > 0
    assert "Food & Dining" in food_rec.title

    # Update status: new -> accepted -> completed
    updated = update_recommendation_status(db, planning_user.id, food_rec.id, "accepted")
    assert updated.status == "accepted"

    # Apply recommendation
    apply_res = apply_recommendation(db, planning_user.id, food_rec.id)
    assert apply_res.success is True
    assert apply_res.recommendation.status == "completed"

def test_goal_simulation_and_feasibility(db: Session, planning_user: User):
    """Verify savings goal feasibility projection and monthly contribution simulation."""
    goals = list_goals(db, planning_user.id)
    assert len(goals) >= 1
    goa_goal = goals[0]

    assert goa_goal.required_monthly_inr > 0
    assert goa_goal.projected_completion_date is not None

    # Simulate boosting monthly contribution to ₹15,000
    sim = simulate_goal_contribution(
        db=db,
        user_id=planning_user.id,
        goal_id=goa_goal.id,
        monthly_contribution_inr=15000.0,
    )

    assert sim.simulated_monthly_contribution_inr == 15000.0
    assert sim.months_to_completion <= 4
    assert sim.is_achievable is True
    assert "ahead of target" in sim.message

def test_deterministic_scenario_simulation_and_persistence(db: Session, planning_user: User):
    """Verify multi-variable scenario simulation and saved scenario CRUD."""
    params = EnhancedSimulationRequest(
        salary_delta_pct=15.0,
        rent_delta_inr=3000.0,
        discretionary_reduction_pct=20.0,
        new_recurring_monthly_inr=5000.0,
        unexpected_expense_inr=20000.0,
        monthly_savings_delta_inr=4000.0,
        horizon_months=12,
    )

    result = run_deterministic_simulation(db, planning_user.id, params)
    assert result.simulated_monthly_income_inr > result.baseline_monthly_income_inr
    assert len(result.trajectory) == 12
    assert result.emergency_reserve_floor_inr > 0

    # Save named scenario
    saved = create_saved_scenario(
        db=db,
        user_id=planning_user.id,
        name="15% Hike + Discretionary Cut",
        description="Simulated promotion and lifestyle optimization",
        params=params,
    )
    assert saved.name == "15% Hike + Discretionary Cut"

    # List saved scenarios
    all_saved = list_saved_scenarios(db, planning_user.id)
    assert any(s.id == saved.id for s in all_saved)

    # Delete scenario
    delete_saved_scenario(db, planning_user.id, saved.id)
    remaining = list_saved_scenarios(db, planning_user.id)
    assert not any(s.id == saved.id for s in remaining)

def test_budget_recommendations_and_application(db: Session, planning_user: User):
    """Verify proactive budget recommendations for essentials and discretionary spending."""
    today = date.today()
    recs = get_budget_recommendations(db, planning_user.id, today.month, today.year)
    assert len(recs.recommendations) >= 1

    # Food & Dining should have a recommended allocation
    food_item = next((r for r in recs.recommendations if "food" in r.category_name.lower()), None)
    assert food_item is not None
    assert food_item.suggested_budget_inr > 0

    # Bulk apply recommendation
    updated_budgets = apply_budget_recommendations(
        db=db,
        user_id=planning_user.id,
        month=today.month,
        year=today.year,
        selected_category_ids=[food_item.category_id],
    )
    assert any(b.category_id == food_item.category_id for b in updated_budgets)

def test_monthly_report_and_csv_export(db: Session, planning_user: User):
    """Verify comprehensive monthly report generation and CSV formatted output."""
    today = date.today()
    rep = generate_monthly_report(db, planning_user.id, today.month, today.year)

    assert rep.total_income_inr > 0
    assert rep.total_expenses_inr > 0
    assert len(rep.category_breakdown) >= 1
    assert rep.month_label == f"{today.strftime('%b')} {today.year}"

    # CSV export
    csv_text = export_monthly_report_csv(db, planning_user.id, today.month, today.year)
    assert "FinPilot AI Monthly Financial Report" in csv_text
    assert "Category Breakdown" in csv_text
    assert "Budget Performance" in csv_text
