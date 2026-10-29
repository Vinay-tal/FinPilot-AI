import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.goal import GoalCreate, GoalUpdate, GoalResponse, GoalSimulationRequest, GoalSimulationResponse
from app.services.goal_service import (
    list_goals,
    get_goal,
    create_goal,
    update_goal,
    delete_goal,
    simulate_goal_contribution,
)

router = APIRouter(prefix="/goals", tags=["Savings Goals"])

@router.get("", response_model=List[GoalResponse])
def get_goals(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[GoalResponse]:
    """List all savings goals and milestones."""
    return list_goals(db, current_user.id)

@router.post("", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
def add_goal(
    goal_in: GoalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    """Create a new savings goal."""
    return create_goal(db, current_user.id, goal_in)

@router.get("/{goal_id}", response_model=GoalResponse)
def get_single_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    """Retrieve details for a single savings goal."""
    return get_goal(db, current_user.id, goal_id)

@router.put("/{goal_id}", response_model=GoalResponse)
def modify_goal(
    goal_id: uuid.UUID,
    goal_in: GoalUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalResponse:
    """Update goal target amount, progress, or priority."""
    return update_goal(db, current_user.id, goal_id, goal_in)

@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_goal(
    goal_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a savings goal."""
    delete_goal(db, current_user.id, goal_id)

@router.post("/{goal_id}/simulate", response_model=GoalSimulationResponse)
def simulate_goal(
    goal_id: uuid.UUID,
    sim_in: GoalSimulationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GoalSimulationResponse:
    """
    Simulate the effect of changing monthly savings contribution on goal completion date,
    projected months, and timeline feasibility.
    """
    return simulate_goal_contribution(
        db=db,
        user_id=current_user.id,
        goal_id=goal_id,
        monthly_contribution_inr=sim_in.monthly_contribution_inr,
    )
