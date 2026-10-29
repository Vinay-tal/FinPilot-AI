import uuid
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.planning import (
    EnhancedSimulationRequest,
    EnhancedSimulationResponse,
    SavedScenarioCreate,
    SavedScenarioResponse,
)
from app.services.simulation_service import (
    run_deterministic_simulation,
    create_saved_scenario,
    list_saved_scenarios,
    get_saved_scenario,
    delete_saved_scenario,
)

router = APIRouter(prefix="/simulation", tags=["Scenario Simulator"])

# Legacy request model for backwards compatibility
class SimulationRequest(BaseModel):
    income_delta_pct: float = Field(default=0.0, description="Percentage change in monthly income (e.g. 10.0 for +10%)")
    rent_delta_inr: float = Field(default=0.0, description="Monthly rent change in INR (e.g. 5000 for +₹5k)")
    discretionary_reduction_pct: float = Field(default=0.0, description="Reduction in dining/shopping (e.g. 15.0 for -15%)")
    new_recurring_monthly_inr: float = Field(default=0.0, description="New monthly obligation (e.g. Car EMI ₹12,000)")
    lump_sum_inr: float = Field(default=0.0, description="One-time inflow (+) or expense (-)")
    monthly_savings_delta_inr: float = Field(default=0.0, description="Additional monthly savings allocation")
    horizon_months: int = Field(default=12, ge=1, le=60)

class TrajectoryPoint(BaseModel):
    month_index: int
    month_label: str
    baseline_savings_inr: float
    simulated_savings_inr: float
    differential_inr: float

class SimulationResponse(BaseModel):
    monthly_baseline_savings_inr: float
    monthly_simulated_savings_inr: float
    monthly_differential_inr: float
    annual_savings_impact_inr: float
    runway_impact_months: float
    emergency_reserve_floor_inr: float = 75000.0
    has_reserve_breach: bool = False
    first_breach_month: Optional[str] = None
    trajectory: List[TrajectoryPoint]

@router.post("/run", response_model=EnhancedSimulationResponse)
def run_scenario(
    req: EnhancedSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> EnhancedSimulationResponse:
    """
    Run deterministic multi-variable financial simulation.
    Calculates projected monthly cash flows, reserve threshold breaches, and goal completion impacts.
    Does NOT mutate actual transaction history.
    """
    return run_deterministic_simulation(db, current_user.id, req)

@router.get("/scenarios", response_model=List[SavedScenarioResponse])
def get_saved_scenarios(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[SavedScenarioResponse]:
    """List all saved named scenarios for the authenticated user."""
    return list_saved_scenarios(db, current_user.id)

@router.post("/scenarios", response_model=SavedScenarioResponse, status_code=status.HTTP_201_CREATED)
def save_named_scenario(
    req: SavedScenarioCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedScenarioResponse:
    """Save a named simulation scenario with its parameters and summary metrics."""
    return create_saved_scenario(
        db=db,
        user_id=current_user.id,
        name=req.name,
        description=req.description,
        params=req.parameters,
    )

@router.get("/scenarios/{scenario_id}", response_model=SavedScenarioResponse)
def get_single_saved_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedScenarioResponse:
    """Retrieve details of a saved scenario."""
    return get_saved_scenario(db, current_user.id, scenario_id)

@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_scenario(
    scenario_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a saved scenario."""
    delete_saved_scenario(db, current_user.id, scenario_id)
