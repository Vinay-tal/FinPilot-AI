from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.schemas.common import HealthResponse, ReadinessResponse
from app.db.session import check_database_connection
from app.core.config import settings

router = APIRouter(tags=["System & Diagnostics"])

@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Liveness probe returning application operational status."""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        service="FinPilot AI Backend",
    )

@router.get("/ready", response_model=ReadinessResponse)
def readiness_check() -> ReadinessResponse:
    """
    Readiness probe validating database connectivity.
    Returns 200 OK if connected, or 503 SERVICE UNAVAILABLE with instructions if database is unreachable.
    """
    is_connected, error_msg = check_database_connection()

    # Mask database URL credentials for security
    raw_url = settings.DATABASE_URL
    if "@" in raw_url:
        protocol_user, host_db = raw_url.split("@", 1)
        protocol = protocol_user.split("://")[0]
        masked_url = f"{protocol}://***:***@{host_db}"
    else:
        masked_url = raw_url

    if not is_connected:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "degraded",
                "database": "disconnected",
                "database_url_masked": masked_url,
                "ai_provider": settings.AI_PROVIDER,
                "diagnostics": {
                    "error": error_msg,
                    "remediation": "Start PostgreSQL container with 'docker compose up -d' or set valid DATABASE_URL in .env"
                }
            }
        )

    return ReadinessResponse(
        status="ready",
        database="connected",
        database_url_masked=masked_url,
        ai_provider=settings.AI_PROVIDER,
        diagnostics={"healthy": True}
    )
