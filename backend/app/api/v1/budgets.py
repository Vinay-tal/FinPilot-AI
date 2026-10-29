import uuid
from datetime import date
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetUpdate, BudgetResponse
from app.schemas.planning import BudgetRecommendationsResponse, ApplyBudgetRecommendationsRequest
from app.services.budget_service import (
    list_budgets,
    create_budget,
    update_budget,
    delete_budget,
    get_budget_recommendations,
    apply_budget_recommendations,
)

router = APIRouter(prefix="/budgets", tags=["Budgets & Pacing"])

@router.get("", response_model=List[BudgetResponse])
def get_budgets(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2020, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BudgetResponse]:
    """Retrieve monthly category budgets with live actuals, remaining allowances, and pacing status."""
    today = date.today()
    m = month or today.month
    y = year or today.year
    return list_budgets(db, current_user.id, m, y)

@router.post("", response_model=BudgetResponse, status_code=status.HTTP_201_CREATED)
def add_budget(
    budget_in: BudgetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetResponse:
    """Create a new monthly category budget allocation."""
    return create_budget(db, current_user.id, budget_in)

@router.put("/{budget_id}", response_model=BudgetResponse)
def modify_budget(
    budget_id: uuid.UUID,
    budget_in: BudgetUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetResponse:
    """Update spending limit or alert threshold for a budget."""
    return update_budget(db, current_user.id, budget_id, budget_in)

@router.delete("/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_budget(
    budget_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Remove a budget allocation."""
    delete_budget(db, current_user.id, budget_id)

@router.get("/recommendations", response_model=BudgetRecommendationsResponse)
def get_recommendations(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2020, le=2100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> BudgetRecommendationsResponse:
    """
    Generate proactive category budget suggestions from 3-month historical spending.
    Includes inflation adjustments for essentials and optimization targets for discretionary expenses.
    """
    today = date.today()
    m = month or today.month
    y = year or today.year
    return get_budget_recommendations(db, current_user.id, m, y)

@router.post("/apply-recommendations", response_model=List[BudgetResponse])
def apply_recommendations(
    req: ApplyBudgetRecommendationsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[BudgetResponse]:
    """Bulk apply suggested budgets for month/year with user overrides."""
    return apply_budget_recommendations(
        db=db,
        user_id=current_user.id,
        month=req.month,
        year=req.year,
        selected_category_ids=req.selected_category_ids,
    )
