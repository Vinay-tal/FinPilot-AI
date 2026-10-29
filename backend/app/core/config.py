from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator
import os
from pathlib import Path

# Build paths inside the project
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "FinPilot AI: Intelligent Personal Financial Advisor for Indian Users"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Database: Default PostgreSQL URL for development & production
    DATABASE_URL: str = "postgresql+psycopg://finpilot:finpilot_password@localhost:5432/finpilot_db"

    # JWT Authentication
    JWT_SECRET: str = "dev_secret_key_change_in_production_finpilot_super_secure_jwt_2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS configuration
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    # AI / LLM Provider configuration
    AI_PROVIDER: str = "mock"
    LLM_PROVIDER: str = "mock"
    GROQ_API_KEY: Optional[str] = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.2

    # Seed demo user credentials
    DEMO_USER_EMAIL: str = "demo@finpilot.in"
    DEMO_USER_PASSWORD: str = "Demo@FinPilot2026!"
    DEMO_USER_NAME: str = "Rahul Sharma"
    DEMO_USER_CURRENCY: str = "INR"

settings = Settings()
