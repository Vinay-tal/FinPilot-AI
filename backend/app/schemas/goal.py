import uuid
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, computed_field

class GoalBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    target_amount_paise: int = Field(..., gt=0, description="Target savings in integer paise")
    current_amount_paise: int = Field(default=0, ge=0, description="Accumulated savings in integer paise")
    target_date: date
    monthly_contribution_paise: int = Field(default=0, ge=0, description="Committed monthly savings in paise")
    category: str = Field(default="SAVINGS", description="EMERGENCY_FUND, VACATION, PURCHASE, INVESTMENT, OTHER")
    priority: str = Field(default="MEDIUM", description="HIGH, MEDIUM, LOW")
    status: str = Field(default="IN_PROGRESS", description="IN_PROGRESS, COMPLETED, PAUSED")

class GoalCreate(GoalBase):
    pass

class GoalUpdate(BaseModel):
    name: Optional[str] = None
    target_amount_paise: Optional[int] = Field(default=None, gt=0)
    current_amount_paise: Optional[int] = Field(default=None, ge=0)
    target_date: Optional[date] = None
    monthly_contribution_paise: Optional[int] = Field(default=None, ge=0)
    category: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None

class GoalResponse(GoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    # Feasibility metrics calculated dynamically by service
    required_monthly_inr: float = 0.0
    projected_completion_date: Optional[date] = None
    is_achievable: bool = True
    feasibility_status: str = "ON_TRACK"
    variance_months: float = 0.0
    cashflow_strain_warning: Optional[str] = None

    @computed_field
    def target_amount_inr(self) -> float:
        return round(self.target_amount_paise / 100.0, 2)

    @computed_field
    def current_amount_inr(self) -> float:
        return round(self.current_amount_paise / 100.0, 2)

    @computed_field
    def monthly_contribution_inr(self) -> float:
        return round(self.monthly_contribution_paise / 100.0, 2)

    @computed_field
    def progress_pct(self) -> float:
        if self.target_amount_paise <= 0:
            return 100.0
        pct = (self.current_amount_paise / self.target_amount_paise) * 100.0
        return round(min(pct, 100.0), 1)

class GoalSimulationRequest(BaseModel):
    monthly_contribution_inr: float = Field(..., gt=0, description="Hypothetical monthly contribution in INR")

class GoalSimulationResponse(BaseModel):
    goal_id: uuid.UUID
    target_amount_inr: float
    current_amount_inr: float
    simulated_monthly_contribution_inr: float
    required_monthly_inr: float
    target_date: date
    simulated_completion_date: date
    months_to_completion: int
    variance_months: float
    is_achievable: bool
    feasibility_status: str
    message: str
