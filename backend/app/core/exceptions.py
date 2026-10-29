from typing import Any, Dict, Optional
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger("finpilot.exceptions")

class AppException(Exception):
    """Base application exception following RFC 7807 structure."""
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}

class NotFoundException(AppException):
    def __init__(self, resource: str, identifier: Any):
        super().__init__(
            message=f"{resource} with identifier '{identifier}' was not found.",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="RESOURCE_NOT_FOUND",
            details={"resource": resource, "identifier": str(identifier)},
        )

class UnauthorizedException(AppException):
    def __init__(self, message: str = "Invalid or expired authentication credentials."):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="UNAUTHORIZED",
        )

class ForbiddenException(AppException):
    def __init__(self, message: str = "You do not have permission to access this resource."):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="FORBIDDEN",
        )

class ConflictException(AppException):
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="RESOURCE_CONFLICT",
            details=details,
        )

class DatabaseUnavailableException(AppException):
    def __init__(
        self,
        message: str = "PostgreSQL database is currently unavailable at the configured host:port. "
                      "Please ensure PostgreSQL is running (e.g. 'docker compose up -d' or local postgres service)."
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="DATABASE_UNAVAILABLE",
            details={"suggestion": "Run 'docker compose up -d' to start PostgreSQL 16 container, or verify DATABASE_URL in .env."}
        )

async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Format custom application exceptions according to RFC 7807."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status_code": exc.status_code,
            "error_code": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "path": request.url.path,
        },
    )

async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions with structured logging."""
    logger.exception(f"Unhandled error on {request.method} {request.url.path}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "status_code": 500,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected internal error occurred. Please consult system logs.",
            "details": {"error_type": type(exc).__name__},
            "path": request.url.path,
        },
    )
