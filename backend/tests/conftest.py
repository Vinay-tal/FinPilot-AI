import os
import uuid
from typing import Generator, Any
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Set test environment flags
os.environ["ENVIRONMENT"] = "testing"
os.environ["DEBUG"] = "false"

from app.db.base import Base
from app.db.session import get_db
from app.db.seed_data import seed_system_categories
from app.main import app

# Create in-memory SQLite database for fast, hermetic test execution
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    """Create all database schema tables once for the test session."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)

@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a clean, isolated database transaction for each test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    # Seed system categories so standard categories always exist
    seed_system_categories(session)
    session.flush()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def db(db_session: Session) -> Session:
    """Convenience alias for db_session."""
    return db_session

@pytest.fixture
def test_user(db_session: Session) -> Any:
    from app.models.user import User
    user = User(
        email=f"tester_{uuid.uuid4().hex[:8]}@finpilot.in",
        password_hash="hashed_pwd",
        full_name="Tester",
        currency="INR",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user

@pytest.fixture
def test_account(db_session: Session, test_user: Any) -> Any:
    from app.models.account import FinancialAccount
    account = FinancialAccount(
        user_id=test_user.id,
        name="HDFC Primary A/C",
        account_type="SAVINGS",
        institution="HDFC Bank",
        account_number_mask="1234",
        balance_paise=5000000,
        currency="INR",
        is_active=True,
    )
    db_session.add(account)
    db_session.flush()
    return account

@pytest.fixture
def test_categories(db_session: Session) -> dict:
    from app.models.category import TransactionCategory
    return {c.slug: c for c in db_session.query(TransactionCategory).all()}

@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """TestClient configured with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def auth_user(client: TestClient) -> dict:
    """Register and authenticate User A."""
    email = f"usera_{uuid.uuid4().hex[:8]}@finpilot.in"
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test User A",
        "currency": "INR",
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    token = data["access_token"]
    user = data["user"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": user,
        "token": token,
    }

@pytest.fixture
def second_auth_user(client: TestClient) -> dict:
    """Register and authenticate User B for cross-tenant isolation testing."""
    email = f"userb_{uuid.uuid4().hex[:8]}@finpilot.in"
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "full_name": "Test User B",
        "currency": "INR",
    }
    res = client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201, res.text
    data = res.json()
    token = data["access_token"]
    user = data["user"]
    return {
        "headers": {"Authorization": f"Bearer {token}"},
        "user": user,
        "token": token,
    }
