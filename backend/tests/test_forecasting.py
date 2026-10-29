import uuid
from datetime import date, timedelta
import pytest
from app.models.transaction import Transaction
from app.models.account import FinancialAccount
from app.models.recurring_transaction import RecurringTransaction
from app.models.category import TransactionCategory
from app.ml.forecasting.cashflow_engine import (
    CashFlowReconstructor,
    BaselineCashFlowModel,
    RidgeCalendarForecastModel,
    CategoryForecastingEngine,
    ShortfallRiskDetector,
    TemporalModelEvaluator,
    ForecastExplainer,
)
from app.services.forecasting_service import (
    generate_forecast_service,
    simulate_stress_scenario_service,
    evaluate_forecasting_models_service,
)


@pytest.fixture
def populated_user_transactions(db, test_user, test_account, test_categories):
    """Seed 60 days of synthetic financial transactions with known properties."""
    today = date.today()
    txs = []

    # 1. Bi-monthly salary credits on day 1
    salary_cat = test_categories["salary"]
    food_cat = test_categories["food-dining"]
    grocery_cat = test_categories["groceries-essentials"]
    util_cat = test_categories["utilities-bills"]

    # Month 1 salary
    txs.append(
        Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=salary_cat.id,
            date=today - timedelta(days=50),
            amount_paise=15000000,  # ₹1,50,000
            transaction_type="CREDIT",
            narration="Tech Corp Salary Credit",
            fingerprint="test_sal_1",
            is_recurring=True,
        )
    )

    # Daily discretionary burns
    for d in range(1, 55):
        tx_dt = today - timedelta(days=d)
        is_weekend = tx_dt.weekday() in (5, 6)
        # Higher spend on weekends (~₹1,500) vs weekdays (~₹600)
        burn_amount = 150000 if is_weekend else 60000

        txs.append(
            Transaction(
                user_id=test_user.id,
                account_id=test_account.id,
                category_id=food_cat.id if d % 2 == 0 else grocery_cat.id,
                date=tx_dt,
                amount_paise=burn_amount,
                transaction_type="DEBIT",
                narration=f"Daily Expense {d}",
                fingerprint=f"test_burn_{d}",
                is_recurring=False,
            )
        )

    # A fixed utility bill
    txs.append(
        Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=util_cat.id,
            date=today - timedelta(days=20),
            amount_paise=250000,  # ₹2,500
            transaction_type="DEBIT",
            narration="Electricity Bill",
            fingerprint="test_bill_1",
            is_recurring=True,
        )
    )

    db.add_all(txs)

    # Add active recurring transactions
    rec_salary = RecurringTransaction(
        user_id=test_user.id,
        category_id=salary_cat.id,
        name="Tech Corp Monthly Salary",
        merchant_name="Tech Corp",
        expected_amount_paise=15000000,
        frequency="MONTHLY",
        next_expected_date=today + timedelta(days=10),
        is_active=True,
    )
    rec_rent = RecurringTransaction(
        user_id=test_user.id,
        category_id=test_categories["housing-rent"].id,
        name="Apartment Monthly Rent",
        merchant_name="Apartment Landlord",
        expected_amount_paise=2500000,  # ₹25,000
        frequency="MONTHLY",
        next_expected_date=today + timedelta(days=8),
        is_active=True,
    )
    db.add_all([rec_salary, rec_rent])
    db.commit()

    return txs


def test_cash_flow_reconstruction(populated_user_transactions, test_account):
    current_liquid_paise = test_account.balance_paise
    df = CashFlowReconstructor.reconstruct_daily_series(
        populated_user_transactions, current_liquid_paise, lookback_days=60
    )

    assert not df.empty
    assert len(df) == 61  # 60 days + today
    assert "balance_paise" in df.columns
    assert "discretionary_debits_paise" in df.columns
    # End balance matches current liquid balance
    assert df["balance_paise"].iloc[-1] == current_liquid_paise


def test_baseline_forecasting_model(populated_user_transactions, test_account):
    current_liquid_paise = test_account.balance_paise
    df = CashFlowReconstructor.reconstruct_daily_series(
        populated_user_transactions, current_liquid_paise, lookback_days=60
    )

    model = BaselineCashFlowModel().fit(df)
    assert model.daily_burn_paise > 0
    # Weekend multiplier should be higher than weekday
    assert model.dow_multipliers[5] >= model.dow_multipliers[1]

    # Predict forward 30 days
    recurring_events = [{
        "name": "Salary Credit",
        "type": "CREDIT",
        "amount_paise": 15000000,
        "expected_date": date.today() + timedelta(days=10),
        "frequency": "MONTHLY",
    }]
    preds = model.predict_daily(date.today(), 30, current_liquid_paise, recurring_events)

    assert len(preds) == 30
    # Uncertainty interval expands forward in time
    spread_day1 = preds[0]["upper_bound_80_inr"] - preds[0]["lower_bound_80_inr"]
    spread_day30 = preds[-1]["upper_bound_80_inr"] - preds[-1]["lower_bound_80_inr"]
    assert spread_day30 > spread_day1


def test_category_forecasting_with_shrinkage(populated_user_transactions, test_categories):
    categories = list(test_categories.values())
    results = CategoryForecastingEngine.forecast_categories(
        populated_user_transactions, categories
    )

    assert len(results) > 0
    # Results should be sorted by projected month end inr descending
    assert results[0]["projected_month_end_inr"] >= results[-1]["projected_month_end_inr"]

    # Categories with spend should have positive projections
    food_res = next((r for r in results if r["category_slug"] == "food-dining"), None)
    assert food_res is not None
    assert food_res["current_spent_inr"] > 0
    assert food_res["projected_month_end_inr"] >= food_res["current_spent_inr"]


def test_shortfall_risk_detection():
    today = date.today()
    # Scenario: Safe trajectory
    safe_points = [
        {
            "date": (today + timedelta(days=i)).isoformat(),
            "balance_paise": 5000000 - (i * 20000),  # ₹50,000 dipping slightly
            "balance_inr": (5000000 - (i * 20000)) / 100.0,
            "upper_bound_80_inr": 60000.0,
        }
        for i in range(1, 31)
    ]
    safe_risk = ShortfallRiskDetector.analyze_risk(safe_points, reserve_threshold_paise=1000000)
    assert not safe_risk["shortfall_detected"]
    assert safe_risk["risk_level"] == "SAFE"

    # Scenario: Shortfall trajectory (balance dips below ₹10,000 on day 15)
    shortfall_points = [
        {
            "date": (today + timedelta(days=i)).isoformat(),
            "balance_paise": 2000000 - (i * 80000),  # dips below 1,000,000 around day 13
            "balance_inr": (2000000 - (i * 80000)) / 100.0,
            "upper_bound_80_inr": 25000.0,
        }
        for i in range(1, 31)
    ]
    shortfall_risk = ShortfallRiskDetector.analyze_risk(
        shortfall_points, reserve_threshold_paise=1000000
    )
    assert shortfall_risk["shortfall_detected"]
    assert shortfall_risk["days_until_shortfall"] is not None
    assert shortfall_risk["risk_level"] in ("HIGH_RISK", "CRITICAL_OVERDRAFT")


def test_temporal_model_evaluation_walk_forward(populated_user_transactions, test_account):
    results = TemporalModelEvaluator.evaluate_models(
        transactions=populated_user_transactions,
        current_liquid_balance_paise=test_account.balance_paise,
        n_splits=2,
        test_window_days=14,
    )

    assert results["status"] == "SUCCESS"
    assert "baseline" in results
    assert "advanced_model" in results
    assert results["baseline"]["mae_inr"] > 0
    assert results["advanced_model"]["mae_inr"] > 0
    assert "improvement_pct" in results


def test_synthetic_stress_scenario_simulation(db, test_user, populated_user_transactions):
    # Test salary delay scenario
    delay_res = simulate_stress_scenario_service(
        db=db,
        user_id=test_user.id,
        scenario_type="SALARY_DELAY",
        horizon_days=30,
        delay_days=10,
    )
    assert delay_res["scenario_type"] == "SALARY_DELAY"
    assert len(delay_res["comparison_points"]) == 30
    assert "shock_description" in delay_res

    # Test emergency expense scenario
    emergency_res = simulate_stress_scenario_service(
        db=db,
        user_id=test_user.id,
        scenario_type="EMERGENCY_EXPENSE",
        expense_amount_inr=30000.0,
    )
    assert emergency_res["scenario_type"] == "EMERGENCY_EXPENSE"
    assert emergency_res["stressed_min_balance_inr"] <= emergency_res["baseline_min_balance_inr"]


def test_forecasting_service_orchestration(db, test_user, populated_user_transactions):
    result = generate_forecast_service(
        db=db,
        user_id=test_user.id,
        horizon_days=30,
        model_type="auto",
        reserve_threshold_inr=10000.0,
        persist=True,
    )

    assert result["horizon_days"] == 30
    assert "model_version" in result
    assert "risk_analysis" in result
    assert "explanation" in result
    assert len(result["forecast_points"]) == 30
    assert len(result["category_forecasts"]) > 0

    # Verify explainability components
    expl = result["explanation"]
    assert len(expl["observed_facts"]) > 0
    assert len(expl["assumptions"]) > 0
    assert "summary_narrative" in expl


def test_forecasting_api_endpoints(client, test_user, populated_user_transactions):
    from app.core.security import create_access_token
    token = create_access_token(str(test_user.id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /forecasting
    resp = client.get("/api/v1/forecasting?days=30", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["horizon_days"] == 30
    assert len(data["forecast_points"]) == 30
    assert "risk_analysis" in data
    assert "explanation" in data

    # 2. GET /forecasting/categories
    cat_resp = client.get("/api/v1/forecasting/categories", headers=headers)
    assert cat_resp.status_code == 200
    categories = cat_resp.json()
    assert isinstance(categories, list)
    assert len(categories) > 0

    # 3. GET /forecasting/evaluation
    eval_resp = client.get("/api/v1/forecasting/evaluation", headers=headers)
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["status"] == "SUCCESS"
    assert "baseline" in eval_data

    # 4. POST /forecasting/scenarios
    scenario_payload = {
        "scenario_type": "EMERGENCY_EXPENSE",
        "horizon_days": 30,
        "expense_amount_inr": 20000.0,
    }
    scen_resp = client.post("/api/v1/forecasting/scenarios", json=scenario_payload, headers=headers)
    assert scen_resp.status_code == 200
    scen_data = scen_resp.json()
    assert scen_data["scenario_type"] == "EMERGENCY_EXPENSE"
    assert len(scen_data["comparison_points"]) == 30
