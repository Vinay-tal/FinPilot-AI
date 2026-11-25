import os
import sys
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
BACKEND_DIR = ROOT_DIR / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Handle database initialization for serverless deployment
db_url = os.environ.get("DATABASE_URL", "")
if not db_url or "sqlite" in db_url:
    tmp_db = Path("/tmp/finpilot.db")
    os.environ["DATABASE_URL"] = f"sqlite:///{tmp_db}"

    # If database doesn't exist yet in /tmp, initialize tables and seed demo data
    try:
        from app.db.base import Base
        from app.db.session import engine, SessionLocal
        from app.db.seed_data import seed_demo_data

        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            from app.models.user import User
            if not db.query(User).first():
                seed_demo_data(db)
        finally:
            db.close()
    except Exception as e:
        print(f"Notice: Serverless DB init: {e}")

from app.main import app
