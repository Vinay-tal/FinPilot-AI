from typing import Generic, TypeVar, List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    """Standardized paginated list response wrapper."""
    items: List[T]
    total: int = Field(..., description="Total count of matching records")
    page: int = Field(..., description="Current page number (1-indexed)")
    limit: int = Field(..., description="Items per page")
    total_pages: int = Field(..., description="Total available pages")

class APIErrorResponse(BaseModel):
    """RFC 7807 error format."""
    status_code: int
    error_code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    path: Optional[str] = None

class HealthResponse(BaseModel):
    """Liveness probe response."""
    status: str = "ok"
    version: str = "1.0.0"
    service: str = "FinPilot AI Backend"

class ReadinessResponse(BaseModel):
    """Readiness probe checking database connectivity."""
    status: str
    database: str
    database_url_masked: str
    ai_provider: str
    diagnostics: Dict[str, Any]
