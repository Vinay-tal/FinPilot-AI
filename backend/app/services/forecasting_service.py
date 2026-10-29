import json
import uuid
from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.account import FinancialAccount
from app.models.transaction import Transaction
from app.models.recurring_transaction import RecurringTransaction
from app.models.category import TransactionCategory
from app.models.forecast import Forecast
from app.models.model_evaluation import ModelEvaluation

from app.ml.forecasting.cashflow_engine import (
    CashFlowReconstructor,
    BaselineCashFlowModel,
    RidgeCalendarForecastModel,
    CategoryForecastingEngine,
    ShortfallRiskDetector,
    TemporalModelEvaluator,
    ForecastExplainer,
)


def get_user_liquid_balance_paise(db: Session, user_id: uuid.UUID) -> int:
    """Calculates total liquid available cash (savings, current, wallets, excluding credit cards)."""
    accounts = db.query(FinancialAccount).filter(
        FinancialAccount.user_id == user_id,
        FinancialAccount.is_active == True,
        FinancialAccount.account_type.in_(["SAVINGS", "CURRENT", "WALLET"]),
    ).all()
    return sum(a.balance_paise for a in accounts)


def get_user_recurring_events(db: Session, user_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Retrieves active recurring transactions and normalizes them for forecasting."""
    recurring = db.query(RecurringTransaction).filter(
        RecurringTransaction.user_id == user_id,
        RecurringTransaction.is_active == True,
    ).all()

    events = []
    for r in recurring:
        # Determine if inflow or outflow
        is_credit = "salary" in r.name.lower() or "dividend" in r.name.lower() or "income" in r.name.lower()
        events.append({
            "id": str(r.id),
            "name": r.name,
            "type": "CREDIT" if is_credit else "DEBIT",
            "amount_paise": r.expected_amount_paise,
            "expected_date": r.next_expected_date,
            "frequency": r.frequency,
        })
    return events


def generate_forecast_service(
    db: Session,
    user_id: uuid.UUID,
    horizon_days: int = 30,
    model_type: str = "auto",
    reserve_threshold_inr: float = 10000.0,
    persist: bool = False,
) -> Dict[str, Any]:
    """
    Main orchestration service for Milestone 4 financial forecasting.
    Reconstructs continuous daily cash flows, runs models, computes prediction intervals,
    detects shortfall risks, generates category forecasts, and factor attributions.
    """
    current_liquid_paise = get_user_liquid_balance_paise(db, user_id)
    reserve_threshold_paise = int(round(reserve_threshold_inr * 100))

    # Pull transactions over past 180 days
    start_lookback = date.today() - timedelta(days=180)
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_lookback,
    ).order_by(Transaction.date.asc()).all()

    # Pull active recurring events
    recurring_events = get_user_recurring_events(db, user_id)

    # Reconstruct continuous daily series
    df = CashFlowReconstructor.reconstruct_daily_series(
        transactions, current_liquid_paise, lookback_days=90
    )

    # Check minimum history requirements
    is_sparse_history = len(transactions) < 5 or len(df) < 14

    # Fit models
    baseline_model = BaselineCashFlowModel().fit(df)
    ridge_model = RidgeCalendarForecastModel().fit(df)

    # Select model based on preference / validation
    selected_version = "baseline_burn_rate_v1"
    if model_type == "ridge" or (model_type == "auto" and ridge_model.is_fitted and not is_sparse_history):
        forecast_points = ridge_model.predict_daily(
            date.today(), horizon_days, current_liquid_paise, recurring_events, df
        )
        selected_version = "ridge_calendar_ml_v1"
    else:
        forecast_points = baseline_model.predict_daily(
            date.today(), horizon_days, current_liquid_paise, recurring_events
        )
        selected_version = "baseline_burn_rate_v1"

    # Evaluate Shortfall Risk
    risk_analysis = ShortfallRiskDetector.analyze_risk(
        forecast_points,
        reserve_threshold_paise=reserve_threshold_paise,
        historical_variance_calibrated=not is_sparse_history,
    )

    # Category Level Forecasts
    categories = db.query(TransactionCategory).all()
    category_forecasts = CategoryForecastingEngine.forecast_categories(
        transactions, categories, as_of_date=date.today()
    )

    # Explainability & Factor Attribution
    daily_burn_inr = round(baseline_model.daily_burn_paise / 100.0, 2)
    end_point = forecast_points[-1] if forecast_points else {"balance_inr": current_liquid_paise / 100.0}
    explanation = ForecastExplainer.generate_explanation(
        current_balance_inr=round(current_liquid_paise / 100.0, 2),
        projected_end_inr=end_point["balance_inr"],
        min_balance_inr=risk_analysis["min_projected_balance_inr"],
        recurring_events=recurring_events,
        daily_burn_inr=daily_burn_inr,
        horizon_days=horizon_days,
        category_forecasts=category_forecasts,
    )

    # Historical context points (last 14 days of reconstructed balance for seamless chart rendering)
    historical_points = []
    if not df.empty:
        tail_14 = df.tail(14)
        for _, row in tail_14.iterrows():
            historical_points.append({
                "date": row["date"].isoformat(),
                "display_date": row["date"].strftime("%b %d"),
                "balance_inr": round(row["balance_inr"], 2),
                "is_historical": True,
            })

    current_inr = round(current_liquid_paise / 100.0, 2)
    end_inr = end_point["balance_inr"]

    response_payload = {
        "horizon_days": horizon_days,
        "model_version": selected_version,
        "is_sparse_history": is_sparse_history,
        "current_balance_inr": current_inr,
        "projected_end_balance_inr": end_inr,
        "net_projected_change_inr": round(end_inr - current_inr, 2),
        "daily_burn_rate_inr": daily_burn_inr,
        "risk_analysis": risk_analysis,
        "explanation": explanation,
        "forecast_points": forecast_points,
        "historical_points": historical_points,
        "category_forecasts": category_forecasts[:8],  # Top 8 categories
    }

    # Persist to database if requested
    if persist and forecast_points:
        persist_forecast_points(
            db=db,
            user_id=user_id,
            points=forecast_points,
            horizon_days=horizon_days,
            model_version=selected_version,
            shortfall_flag=risk_analysis["shortfall_detected"],
        )

    return response_payload


def persist_forecast_points(
    db: Session,
    user_id: uuid.UUID,
    points: List[Dict[str, Any]],
    horizon_days: int,
    model_version: str,
    shortfall_flag: bool,
) -> None:
    """Store daily projection points in the forecasts table."""
    try:
        # Clear previous forecast for same user and today's target dates
        db.query(Forecast).filter(Forecast.user_id == user_id).delete()

        for pt in points:
            fc_dt = date.fromisoformat(pt["date"])
            fc_record = Forecast(
                user_id=user_id,
                forecast_date=fc_dt,
                horizon_days=horizon_days,
                predicted_balance_paise=pt["balance_paise"],
                lower_bound_80_paise=int(round(pt["lower_bound_80_inr"] * 100)),
                upper_bound_80_paise=int(round(pt["upper_bound_80_inr"] * 100)),
                lower_bound_95_paise=int(round(pt["lower_bound_95_inr"] * 100)),
                upper_bound_95_paise=int(round(pt["upper_bound_95_inr"] * 100)),
                projected_net_change_paise=int(round(pt["recurring_net_inr"] * 100)) - int(round(pt["discretionary_burn_inr"] * 100)),
                shortfall_flag=shortfall_flag,
                model_version=model_version,
            )
            db.add(fc_record)

        db.flush()
    except Exception:
        db.rollback()


def get_latest_persisted_forecast_service(
    db: Session,
    user_id: uuid.UUID,
) -> Optional[Dict[str, Any]]:
    """Retrieve active forecast points previously stored in the database."""
    records = db.query(Forecast).filter(
        Forecast.user_id == user_id
    ).order_by(Forecast.forecast_date.asc()).all()

    if not records:
        return None

    first = records[0]
    last = records[-1]
    points = [
        {
            "date": r.forecast_date.isoformat(),
            "display_date": r.forecast_date.strftime("%b %d"),
            "balance_inr": round(r.predicted_balance_paise / 100.0, 2),
            "lower_bound_80_inr": round(r.lower_bound_80_paise / 100.0, 2),
            "upper_bound_80_inr": round(r.upper_bound_80_paise / 100.0, 2),
            "lower_bound_95_inr": round(r.lower_bound_95_paise / 100.0, 2),
            "upper_bound_95_inr": round(r.upper_bound_95_paise / 100.0, 2),
        }
        for r in records
    ]

    return {
        "model_version": first.model_version,
        "horizon_days": first.horizon_days,
        "created_at": first.created_at.isoformat(),
        "start_balance_inr": round(first.predicted_balance_paise / 100.0, 2),
        "end_balance_inr": round(last.predicted_balance_paise / 100.0, 2),
        "total_days": len(records),
        "points": points,
    }


def evaluate_forecasting_models_service(
    db: Session,
    user_id: uuid.UUID,
) -> Dict[str, Any]:
    """Execute temporal train/test split cross validation and log metrics."""
    liquid_paise = get_user_liquid_balance_paise(db, user_id)
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).order_by(Transaction.date.asc()).all()

    results = TemporalModelEvaluator.evaluate_models(
        transactions=transactions,
        current_liquid_balance_paise=liquid_paise,
        n_splits=3,
        test_window_days=14,
    )

    # Persist evaluation record
    if results.get("status") == "SUCCESS":
        try:
            eval_record = ModelEvaluation(
                model_name="cashflow_forecaster",
                version=results["model_version"],
                evaluation_type="WALK_FORWARD_TEMPORAL_CV",
                metrics_json=json.dumps(results),
                sample_size=results.get("data_coverage_days", 90),
            )
            db.add(eval_record)
            db.flush()
            results["evaluation_id"] = str(eval_record.id)
        except Exception:
            pass

    return results


def simulate_stress_scenario_service(
    db: Session,
    user_id: uuid.UUID,
    scenario_type: str,
    horizon_days: int = 30,
    delay_days: int = 7,
    expense_amount_inr: float = 25000.0,
    spend_surge_pct: float = 40.0,
) -> Dict[str, Any]:
    """
    Stress-testing engine: simulates synthetic shocks on top of the cash-flow trajectory.
    1. SALARY_DELAY: delays recurring income credits by N days.
    2. EMERGENCY_EXPENSE: injects unexpected capital outflow on Day 5.
    3. SPENDING_SURGE: increases daily discretionary burn rate by X%.
    """
    current_liquid_paise = get_user_liquid_balance_paise(db, user_id)
    recurring_events = get_user_recurring_events(db, user_id)

    # Pull transactions
    transactions = db.query(Transaction).filter(
        Transaction.user_id == user_id
    ).all()
    df = CashFlowReconstructor.reconstruct_daily_series(
        transactions, current_liquid_paise, lookback_days=90
    )
    baseline_model = BaselineCashFlowModel().fit(df)

    # Run unmodified baseline
    baseline_points = baseline_model.predict_daily(
        date.today(), horizon_days, current_liquid_paise, recurring_events
    )

    # Apply stress modifications
    stressed_events = [dict(e) for e in recurring_events]
    stressed_burn_paise = baseline_model.daily_burn_paise

    shock_description = ""
    if scenario_type == "SALARY_DELAY":
        shock_description = f"Expected salary/income credited is delayed by {delay_days} days."
        for ev in stressed_events:
            if ev["type"] == "CREDIT":
                orig_dt = ev["expected_date"]
                ev["expected_date"] = orig_dt + timedelta(days=delay_days)

    elif scenario_type == "EMERGENCY_EXPENSE":
        shock_description = f"Unexpected capital expense of ₹{expense_amount_inr:,.0f} occurs on Day 5."
        expense_paise = int(round(expense_amount_inr * 100))
        stressed_events.append({
            "id": "stress_emergency",
            "name": f"Emergency Expense (₹{expense_amount_inr:,.0f})",
            "type": "DEBIT",
            "amount_paise": expense_paise,
            "expected_date": date.today() + timedelta(days=5),
            "frequency": "ONEOFF",
        })

    elif scenario_type == "SPENDING_SURGE":
        surge_factor = 1.0 + (spend_surge_pct / 100.0)
        stressed_burn_paise = int(baseline_model.daily_burn_paise * surge_factor)
        shock_description = f"Discretionary living expenses surge by +{spend_surge_pct:.0f}% (₹{stressed_burn_paise // 100:,.0f}/day vs baseline ₹{baseline_model.daily_burn_paise // 100:,.0f}/day)."

    # Temporarily set model burn and predict stressed trajectory
    stressed_model = BaselineCashFlowModel()
    stressed_model.daily_burn_paise = stressed_burn_paise
    stressed_model.dow_multipliers = baseline_model.dow_multipliers
    stressed_model.residual_std_paise = baseline_model.residual_std_paise

    stressed_points = stressed_model.predict_daily(
        date.today(), horizon_days, current_liquid_paise, stressed_events
    )

    # Compare risk outcomes
    base_risk = ShortfallRiskDetector.analyze_risk(baseline_points)
    stressed_risk = ShortfallRiskDetector.analyze_risk(stressed_points)

    base_end = baseline_points[-1]["balance_inr"] if baseline_points else 0.0
    stressed_end = stressed_points[-1]["balance_inr"] if stressed_points else 0.0

    return {
        "scenario_type": scenario_type,
        "shock_description": shock_description,
        "horizon_days": horizon_days,
        "baseline_end_balance_inr": base_end,
        "stressed_end_balance_inr": stressed_end,
        "delta_end_balance_inr": round(stressed_end - base_end, 2),
        "baseline_min_balance_inr": base_risk["min_projected_balance_inr"],
        "stressed_min_balance_inr": stressed_risk["min_projected_balance_inr"],
        "shortfall_induced": stressed_risk["shortfall_detected"] and not base_risk["shortfall_detected"],
        "stressed_shortfall_date": stressed_risk["shortfall_date"],
        "stressed_probability_pct": stressed_risk["shortfall_probability_pct"],
        "stressed_risk_level": stressed_risk["risk_level"],
        "comparison_points": [
            {
                "date": b["date"],
                "display_date": b["display_date"],
                "baseline_balance_inr": b["balance_inr"],
                "stressed_balance_inr": s["balance_inr"],
                "event_name": s["event_name"],
            }
            for b, s in zip(baseline_points, stressed_points)
        ],
    }
