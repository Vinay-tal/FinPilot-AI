from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.dashboard import DashboardSummaryResponse, CashflowTrendItem, CategorySpendItem
from app.services.dashboard_service import (
    get_dashboard_summary,
    get_cashflow_trend,
    get_category_breakdown,
)

router = APIRouter(prefix="/dashboard", tags=["Financial Dashboard"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def dashboard_summary(
    period: str = Query(
        default="current_month",
        description="Time period: current_month, last_30_days, last_90_days, ytd"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    """Retrieve top-level financial metrics, net cash flow, savings rate, balances, and health score."""
    return get_dashboard_summary(db, current_user.id, period)

@router.get("/cashflow-trend", response_model=List[CashflowTrendItem])
def cashflow_trend(
    months: int = Query(default=6, ge=1, le=24, description="Number of historical months to return"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CashflowTrendItem]:
    """Retrieve monthly historical income vs expenses trend."""
    return get_cashflow_trend(db, current_user.id, months)

@router.get("/category-breakdown", response_model=List[CategorySpendItem])
def category_breakdown(
    period: str = Query(default="current_month", description="current_month, last_30_days, last_90_days, ytd"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[CategorySpendItem]:
    """Retrieve category-level expenditure distribution and percentages."""
    return get_category_breakdown(db, current_user.id, period)
