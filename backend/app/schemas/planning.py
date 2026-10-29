import uuid
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

# --- Financial Health Score Schemas ---

class HealthFactorItem(BaseModel):
    factor_id: str
    name: str
    weight: int
    score: float
    max_score: float
    normalized_pct: float
    is_excluded: bool = False
    exclusion_reason: Optional[str] = None
    metric_value: Optional[str] = None
    calculation_details: str
    actionable_tip: str

class HealthScoreResponse(BaseModel):
    overall_score: int
    grade: str
    disclaimer: str = (
        "Educational heuristic model for personal financial awareness. "
        "This is not a credit score or a validated measure of creditworthiness."
    )
    summary: str
    liquid_reserve_inr: float
    monthly_expenses_inr: float
    savings_rate_pct: float
    factors: List[HealthFactorItem]
    excluded_factors_count: int
    top_improvement_actions: List[str]

# --- Scenario Simulation & Saved Scenarios Schemas ---

class EnhancedSimulationRequest(BaseModel):
    name: Optional[str] = Field(default=None, description="Optional name if saving immediately")
    description: Optional[str] = Field(default=None, description="Optional scenario notes")
    salary_delta_pct: float = Field(default=0.0, description="Salary/income change percentage (e.g. 10.0 for +10%)")
    rent_delta_inr: float = Field(default=0.0, description="Rent change in INR (e.g. 3000 for +₹3,000/mo)")
    discretionary_reduction_pct: float = Field(default=0.0, description="Reduction in discretionary categories (e.g. 15.0 for -15%)")
    new_recurring_monthly_inr: float = Field(default=0.0, description="New recurring monthly expense (e.g. ₹12,000 car EMI)")
    unexpected_expense_inr: float = Field(default=0.0, description="One-time unexpected expense in Month 1 (e.g. ₹25,000)")
    monthly_savings_delta_inr: float = Field(default=0.0, description="Adjustment to monthly savings contribution (e.g. +₹5,000)")
    horizon_months: int = Field(default=12, ge=1, le=60, description="Projection horizon in months")

class SimulationTrajectoryPoint(BaseModel):
    month_index: int
    month_label: str
    baseline_income_inr: float
    simulated_income_inr: float
    baseline_expense_inr: float
    simulated_expense_inr: float
    baseline_net_cashflow_inr: float
    simulated_net_cashflow_inr: float
    cumulative_baseline_balance_inr: float
    cumulative_simulated_balance_inr: float
    is_breached: bool
    breach_gap_inr: float

class GoalImpactItem(BaseModel):
    goal_id: str
    goal_name: str
    original_completion_date: str
    simulated_completion_date: str
    variance_months: float
    status_change: str

class EnhancedSimulationResponse(BaseModel):
    baseline_monthly_income_inr: float
    simulated_monthly_income_inr: float
    baseline_monthly_expense_inr: float
    simulated_monthly_expense_inr: float
    baseline_monthly_savings_inr: float
    simulated_monthly_savings_inr: float
    net_monthly_differential_inr: float
    annual_savings_impact_inr: float
    emergency_reserve_floor_inr: float
    has_reserve_breach: bool
    first_breach_month: Optional[str] = None
    min_projected_balance_inr: float
    goal_impacts: List[GoalImpactItem]
    trajectory: List[SimulationTrajectoryPoint]

class SavedScenarioCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = None
    parameters: EnhancedSimulationRequest

class SavedScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: Optional[str] = None
    params_json: str
    results_summary_json: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# --- Budget Recommendations Schemas ---

class BudgetRecommendationItem(BaseModel):
    category_id: uuid.UUID
    category_name: str
    category_color: Optional[str] = None
    is_essential: bool
    historical_avg_spent_inr: float
    suggested_budget_inr: float
    suggested_budget_paise: int
    current_budget_inr: Optional[float] = None
    variance_pct: float
    rationale: str

class BudgetRecommendationsResponse(BaseModel):
    month: int
    year: int
    total_suggested_inr: float
    recommendations: List[BudgetRecommendationItem]

class ApplyBudgetRecommendationsRequest(BaseModel):
    month: int
    year: int
    selected_category_ids: Optional[List[uuid.UUID]] = None

# --- Monthly Reports Schemas ---

class CategoryReportItem(BaseModel):
    category_name: str
    category_color: Optional[str] = None
    spent_inr: float
    share_pct: float
    mom_change_inr: float
    mom_change_pct: float

class BudgetPerformanceReportItem(BaseModel):
    category_name: str
    budgeted_inr: float
    spent_inr: float
    variance_inr: float
    pacing_pct: float
    status: str

class MonthlyReportResponse(BaseModel):
    month: int
    year: int
    month_label: str
    total_income_inr: float
    total_expenses_inr: float
    net_savings_inr: float
    savings_rate_pct: float
    total_liquid_balance_inr: float
    accounts_count: int
    transactions_count: int
    category_breakdown: List[CategoryReportItem]
    budget_performance: List[BudgetPerformanceReportItem]
    total_budgeted_inr: float
    total_budget_spent_inr: float
    budget_utilization_pct: float
    forecast_month_end_balance_inr: Optional[float] = None
    actual_vs_forecast_delta_inr: Optional[float] = None
    anomalies_detected: List[str]
    recommendation_summary: Dict[str, int]
    generated_at: datetime

# --- Notification Schemas ---

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    message: str
    notification_type: str
    is_read: bool
    action_url: Optional[str] = None
    created_at: datetime
