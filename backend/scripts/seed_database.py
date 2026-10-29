import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.db.base import Base
from app.db.session import engine, SessionLocal, check_database_connection
from app.db.seed_data import seed_demo_data
from app.core.config import settings

def main():
    print(f"Connecting to database: {settings.DATABASE_URL}")
    is_connected, error_msg = check_database_connection()
    if not is_connected:
        print(f"\n[ERROR] Unable to connect to configured database:")
        print(f"Details: {error_msg}")
        print("\nRemediation:")
        print("1. If using Docker Compose for PostgreSQL, run:")
        print("   docker compose up -d")
        print("2. If using local SQLite for development, update .env with:")
        print("   DATABASE_URL=\"sqlite:///./finpilot.db\"")
        sys.exit(1)

    print("Creating all database tables via SQLAlchemy 2.0 metadata...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully.")

    print(f"Seeding synthetic Indian financial demo persona ({settings.DEMO_USER_NAME} <{settings.DEMO_USER_EMAIL}>)...")
    db = SessionLocal()
    try:
        user = seed_demo_data(db)
        print(f"Successfully seeded demo persona:")
        print(f"  User ID : {user.id}")
        print(f"  Email   : {user.email}")
        print(f"  Password: {settings.DEMO_USER_PASSWORD}")
        print(f"  Status  : Seeded with accounts, 12 months of realistic Indian transactions, budgets, and goals.")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] Failed to seed data: {exc}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()
