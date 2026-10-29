from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import AppException, app_exception_handler, unhandled_exception_handler
from app.api.v1 import (
    system,
    auth,
    accounts,
    categories,
    transactions,
    budgets,
    goals,
    dashboard,
    recurring,
    insights,
    forecasting,
    simulation,
    copilot,
    ingestion,
    intelligence,
    planning,
    recommendations,
)

# Initialize structured logging
setup_logging()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Intelligent Personal Financial Advisor tailored for Indian users with UPI transaction parsing, "
                "time-series forecasting, anomaly detection, explainable financial health scoring, and AI advisory.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom security middlewares
from app.core.middleware import (
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    RateLimitMiddleware,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestSizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)

# Exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(Exception, unhandled_exception_handler)

# Register API routers under /api/v1
app.include_router(system.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(accounts.router, prefix=settings.API_V1_STR)
app.include_router(categories.router, prefix=settings.API_V1_STR)
app.include_router(transactions.router, prefix=settings.API_V1_STR)
app.include_router(budgets.router, prefix=settings.API_V1_STR)
app.include_router(goals.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(recurring.router, prefix=settings.API_V1_STR)
app.include_router(insights.router, prefix=settings.API_V1_STR)
app.include_router(forecasting.router, prefix=settings.API_V1_STR)
app.include_router(simulation.router, prefix=settings.API_V1_STR)
app.include_router(copilot.router, prefix=settings.API_V1_STR)
app.include_router(ingestion.router, prefix=settings.API_V1_STR)
app.include_router(intelligence.router, prefix=settings.API_V1_STR)
app.include_router(planning.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)

@app.get("/", tags=["Root"])
def root_redirect():
    """Welcome index with links to API documentation and system status."""
    return {
        "project": settings.PROJECT_NAME,
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": f"{settings.API_V1_STR}/health",
        "readiness_check": f"{settings.API_V1_STR}/ready",
    }
