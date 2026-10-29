import uuid
from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.notification import UserNotification
from app.schemas.planning import (
    HealthScoreResponse,
    MonthlyReportResponse,
    NotificationResponse,
)
from app.services.planning_service import (
    calculate_financial_health_score,
    generate_monthly_report,
    export_monthly_report_csv,
    generate_system_alerts,
)
from app.core.exceptions import NotFoundException, ForbiddenException

router = APIRouter(tags=["Planning, Health Score & Reports"])

@router.get("/planning/health-score", response_model=HealthScoreResponse)
def get_health_score(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> HealthScoreResponse:
    """
    Retrieve explainable financial health score (0-100) with detailed factor breakdowns,
    normalized weights, missing data exclusions, and actionable improvement recommendations.
    Educational heuristic disclaimer included.
    """
    return calculate_financial_health_score(db, current_user.id)

@router.get("/reports/monthly", response_model=MonthlyReportResponse)
def get_monthly_report(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2020, le=2030),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonthlyReportResponse:
    """
    Retrieve monthly financial report dossier containing income/expenses,
    category breakdowns, budget performance, forecast vs actuals, and anomalies.
    """
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year
    return generate_monthly_report(db, current_user.id, target_month, target_year)

@router.get("/reports/export/csv")
def download_monthly_report_csv(
    month: Optional[int] = Query(default=None, ge=1, le=12),
    year: Optional[int] = Query(default=None, ge=2020, le=2030),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download monthly financial report summary as CSV."""
    today = date.today()
    target_month = month or today.month
    target_year = year or today.year
    csv_text = export_monthly_report_csv(db, current_user.id, target_month, target_year)

    filename = f"FinPilot_Report_{target_month}_{target_year}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )

@router.get("/notifications", response_model=List[NotificationResponse])
def get_user_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[NotificationResponse]:
    """Retrieve user in-app notifications and trigger evaluation for budget/forecast alerts."""
    return generate_system_alerts(db, current_user.id)

@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationResponse:
    """Mark a notification as read."""
    note = db.query(UserNotification).filter(UserNotification.id == notification_id).first()
    if not note:
        raise NotFoundException("UserNotification", notification_id)
    if note.user_id != current_user.id:
        raise ForbiddenException("You cannot modify another user's notification.")

    note.is_read = True
    db.flush()
    return NotificationResponse.model_validate(note)

@router.post("/notifications/read-all", status_code=status.HTTP_200_OK)
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read."""
    db.query(UserNotification).filter(
        UserNotification.user_id == current_user.id,
        UserNotification.is_read == False,
    ).update({"is_read": True})
    db.flush()
    return {"message": "All notifications marked as read."}
