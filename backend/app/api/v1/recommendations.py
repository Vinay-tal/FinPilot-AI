import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.recommendation import (
    RecommendationResponse,
    RecommendationStatusUpdate,
    RecommendationApplyResponse,
)
from app.services.recommendation_service import (
    list_recommendations,
    generate_personalized_recommendations,
    update_recommendation_status,
    apply_recommendation,
)

router = APIRouter(prefix="/recommendations", tags=["Personalized Recommendations"])

@router.get("", response_model=List[RecommendationResponse])
def get_recommendations(
    status: Optional[str] = Query(default=None, description="Filter: new, accepted, dismissed, completed, all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecommendationResponse]:
    """Retrieve personalized financial recommendations with impact estimates and status."""
    recs = list_recommendations(db, current_user.id, status)
    if not recs and (status is None or status == "all" or status == "new"):
        # Automatically generate if empty
        recs = generate_personalized_recommendations(db, current_user.id)
    return recs

@router.post("/generate", response_model=List[RecommendationResponse])
def trigger_recommendation_generation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[RecommendationResponse]:
    """Trigger recommendation engine evaluation based on current spending, budgets, and bills."""
    return generate_personalized_recommendations(db, current_user.id)

@router.patch("/{recommendation_id}/status", response_model=RecommendationResponse)
def change_recommendation_status(
    recommendation_id: uuid.UUID,
    req: RecommendationStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationResponse:
    """Update recommendation state: accepted, dismissed, or completed."""
    return update_recommendation_status(db, current_user.id, recommendation_id, req.status)

@router.post("/{recommendation_id}/apply", response_model=RecommendationApplyResponse)
def execute_recommendation_action(
    recommendation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RecommendationApplyResponse:
    """Execute recommended concrete action (e.g., updating budget or goal)."""
    return apply_recommendation(db, current_user.id, recommendation_id)
