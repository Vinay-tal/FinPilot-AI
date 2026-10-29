import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.financial_insight import FinancialInsight
from app.schemas.insights import InsightResponse
from app.core.exceptions import NotFoundException, ForbiddenException

router = APIRouter(prefix="/insights", tags=["Insights & Anomalies"])

@router.get("", response_model=List[InsightResponse])
def get_insights(
    is_resolved: Optional[bool] = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[InsightResponse]:
    """Retrieve financial insights and detected anomalies."""
    query = db.query(FinancialInsight).filter(FinancialInsight.user_id == current_user.id)
    if is_resolved is not None:
        query = query.filter(FinancialInsight.is_resolved == is_resolved)
    
    insights = query.order_by(FinancialInsight.created_at.desc()).all()
    return [InsightResponse.model_validate(i) for i in insights]

@router.post("/{insight_id}/resolve", response_model=InsightResponse)
def resolve_insight(
    insight_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> InsightResponse:
    """Mark an insight or anomaly as resolved."""
    insight = db.query(FinancialInsight).filter(FinancialInsight.id == insight_id).first()
    if not insight:
        raise NotFoundException("FinancialInsight", insight_id)
    if insight.user_id != current_user.id:
        raise ForbiddenException("You cannot resolve another user's insight.")
    
    insight.is_resolved = True
    insight.is_read = True
    db.flush()
    return InsightResponse.model_validate(insight)
