from typing import Generator, Tuple, Optional
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings
from app.core.exceptions import DatabaseUnavailableException
import logging

logger = logging.getLogger("finpilot.db")

# Create engine with appropriate pool settings
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = sa.create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_database_connection() -> Tuple[bool, Optional[str]]:
    """
    Check if the configured database (e.g., PostgreSQL) is reachable.
    Returns (True, None) on success, or (False, error_details) on failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))
        return True, None
    except Exception as exc:
        err_msg = str(exc)
        logger.warning(f"Database health check failed: {err_msg}")
        return False, err_msg

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a transactional database session.
    Closes and rolls back on exception, commits on success.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as exc:
        db.rollback()
        # If it's a database connection error (e.g. Postgres is down)
        if "connection" in str(exc).lower() or "operationalerror" in str(exc).lower():
            raise DatabaseUnavailableException()
        raise exc
    finally:
        db.close()
