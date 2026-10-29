import uuid
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.services.forecasting_service import (
    generate_forecast_service,
    get_latest_persisted_forecast_service,
    evaluate_forecasting_models_service,
    simulate_stress_scenario_service,
)
from app.ml.forecasting.cashflow_engine import CategoryForecastingEngine
from app.models.transaction import Transaction
from app.models.category import TransactionCategory

router = APIRouter(prefix="/forecasting", tags=["Cash-Flow Forecasting"])


class ForecastPoint(BaseModel):
    date: str
    display_date: Optional[str] = None
    balance_inr: float
    lower_bound_inr: float
    upper_bound_inr: float
    lower_bound_95_inr: Optional[float] = None
    upper_bound_95_inr: Optional[float] = None
    discretionary_burn_inr: Optional[float] = None
    recurring_net_inr: Optional[float] = None
    event_name: Optional[str] = None


class HistoricalPoint(BaseModel):
    date: str
    display_date: str
    balance_inr: float
    is_historical: bool = True


class ShortfallRiskInfo(BaseModel):
    shortfall_detected: bool
    shortfall_date: Optional[str] = None
    min_projected_balance_inr: float
    risk_level: str
    shortfall_probability_pct: float
    probability_calibrated: bool
    days_until_shortfall: Optional[int] = None
    buffer_deficit_inr: float
    reserve_threshold_inr: float


class DriverItem(BaseModel):
    factor: str
    impact_inr: float
    description: str


class ForecastExplanation(BaseModel):
    summary_narrative: str
    observed_facts: List[str]
    assumptions: List[str]
    positive_drivers: List[DriverItem]
    negative_drivers: List[DriverItem]


class CategoryForecastItem(BaseModel):
    category_id: str
    category_name: str
    category_slug: str
    category_color: str
    current_spent_inr: float
    projected_remaining_inr: float
    projected_month_end_inr: float
    daily_run_rate_inr: float
    pacing_status: str
    pacing_ratio: float
    historical_90d_total_inr: float


class ForecastResponse(BaseModel):
    horizon_days: int
    model_version: str = "baseline_burn_rate_v1"
    is_sparse_history: bool = False
    current_balance_inr: float
    projected_end_balance_inr: float
    net_projected_change_inr: float
    daily_burn_rate_inr: float = 0.0
    shortfall_detected: bool
    shortfall_date: Optional[str] = None
    min_projected_balance_inr: float
    risk_analysis: ShortfallRiskInfo
    explanation: ForecastExplanation
    forecast_points: List[ForecastPoint]
    historical_points: List[HistoricalPoint] = []
    category_forecasts: List[CategoryForecastItem] = []


class StressScenarioRequest(BaseModel):
    scenario_type: str = Field(..., description="SALARY_DELAY, EMERGENCY_EXPENSE, or SPENDING_SURGE")
    horizon_days: int = 30
    delay_days: int = 7
    expense_amount_inr: float = 25000.0
    spend_surge_pct: float = 40.0


@router.get("", response_model=ForecastResponse)
def get_forecast(
    days: int = Query(default=30, ge=7, le=90),
    model_type: str = Query(default="auto", pattern="^(auto|baseline|ridge|holt_winters)$"),
    reserve_threshold_inr: float = Query(default=10000.0, ge=0.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    """Generate forward-looking daily cash flow projection with uncertainty intervals and risk analysis."""
    result = generate_forecast_service(
        db=db,
        user_id=current_user.id,
        horizon_days=days,
        model_type=model_type,
        reserve_threshold_inr=reserve_threshold_inr,
        persist=False,
    )
    # Map for backwards compatibility
    result["shortfall_detected"] = result["risk_analysis"]["shortfall_detected"]
    result["shortfall_date"] = result["risk_analysis"]["shortfall_date"]
    result["min_projected_balance_inr"] = result["risk_analysis"]["min_projected_balance_inr"]
    return ForecastResponse(**result)


@router.post("/generate", response_model=ForecastResponse)
def generate_and_save_forecast(
    days: int = Query(default=30, ge=7, le=90),
    model_type: str = Query(default="auto", pattern="^(auto|baseline|ridge|holt_winters)$"),
    reserve_threshold_inr: float = Query(default=10000.0, ge=0.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ForecastResponse:
    """Generate and persist forward-looking cash flow forecast points to database."""
    result = generate_forecast_service(
        db=db,
        user_id=current_user.id,
        horizon_days=days,
        model_type=model_type,
        reserve_threshold_inr=reserve_threshold_inr,
        persist=True,
    )
    result["shortfall_detected"] = result["risk_analysis"]["shortfall_detected"]
    result["shortfall_date"] = result["risk_analysis"]["shortfall_date"]
    result["min_projected_balance_inr"] = result["risk_analysis"]["min_projected_balance_inr"]
    return ForecastResponse(**result)


@router.get("/latest")
def get_latest_forecast(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve the latest persisted forecast from database."""
    latest = get_latest_persisted_forecast_service(db, current_user.id)
    if not latest:
        # Fallback to generating on the fly
        generated = generate_forecast_service(db, current_user.id, horizon_days=30, persist=True)
        return generated
    return latest


@router.get("/categories", response_model=List[CategoryForecastItem])
def get_category_forecasts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CategoryForecastItem]:
    """Forecast month-end spending per category with shrinkage and pacing indicators."""
    transactions = db.query(Transaction).filter(
        Transaction.user_id == current_user.id
    ).all()
    categories = db.query(TransactionCategory).all()

    results = CategoryForecastingEngine.forecast_categories(transactions, categories)
    return [CategoryForecastItem(**r) for r in results]


@router.get("/evaluation")
def get_model_evaluation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Perform temporal train/test split cross validation and compare baseline vs ML models."""
    return evaluate_forecasting_models_service(db, current_user.id)


@router.post("/scenarios")
def simulate_scenario(
    body: StressScenarioRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Simulate synthetic stress test scenarios (salary delay, emergency expense, spending surge)."""
    return simulate_stress_scenario_service(
        db=db,
        user_id=current_user.id,
        scenario_type=body.scenario_type,
        horizon_days=body.horizon_days,
        delay_days=body.delay_days,
        expense_amount_inr=body.expense_amount_inr,
        spend_surge_pct=body.spend_surge_pct,
    )
