import uuid
from datetime import date, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.models.category import TransactionCategory
from app.models.account import FinancialAccount
from app.models.recurring_transaction import RecurringTransaction
from app.models.chat import ChatConversation, ChatMessage
from app.ml.copilot.provider import MockLLMProvider
from app.ml.copilot.guardrails import sanitize_user_input, check_out_of_scope
from app.ml.copilot.tools import (
    QueryTransactionsInput,
    execute_query_transactions,
    ComparePeriodsInput,
    execute_compare_periods,
    GetRecurringInput,
    execute_get_recurring,
    SimulateScenarioInput,
    execute_simulate_scenario,
)

# ============================================================================
# 1. Mock Provider Intent Mapping & Determinism
# ============================================================================

def test_mock_provider_intent_mapping():
    provider = MockLLMProvider()

    # 1. Food spend
    res = provider.generate([{"role": "user", "content": "How much did I spend on food this month?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "query_aggregate_transactions"

    # 2. Category increase vs last month
    res = provider.generate([{"role": "user", "content": "Which categories increased the most compared with last month?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "compare_time_periods"

    # 3. Afford purchase without dropping below reserve
    res = provider.generate([{"role": "user", "content": "Can I afford a ₹15,000 purchase without dropping below my emergency reserve?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "simulate_financial_scenario"

    # 4. Predict low balance
    res = provider.generate([{"role": "user", "content": "Why does the system predict a low balance near month-end?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "get_cashflow_forecast"

    # 5. Reduce spending by ₹2,000
    res = provider.generate([{"role": "user", "content": "Where could I reduce spending by ₹2,000 next month?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "simulate_financial_scenario"

    # 6. Recurring payments due soon
    res = provider.generate([{"role": "user", "content": "What recurring payments are due soon?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "get_recurring_payments"

    # 7. Six months savings
    res = provider.generate([{"role": "user", "content": "How much could I save in six months under different spending assumptions?"}])
    assert len(res.tool_calls) == 1
    assert res.tool_calls[0]["function"]["name"] == "simulate_financial_scenario"

# ============================================================================
# 2. Deterministic Tool Numerical Accuracy
# ============================================================================

def test_deterministic_query_transactions_accuracy(db_session: Session, test_user, test_account, test_categories):
    today = date.today()
    food_cat = test_categories["food-dining"]

    # Seed 2 food transactions
    t1 = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=food_cat.id,
        date=today,
        amount_paise=85000,  # ₹850
        transaction_type="DEBIT",
        narration="Swiggy Order #981",
        merchant_name="Swiggy",
        fingerprint=f"fp-swiggy-{uuid.uuid4().hex}",
    )
    t2 = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=food_cat.id,
        date=today,
        amount_paise=65000,  # ₹650
        transaction_type="DEBIT",
        narration="Zomato Lunch",
        merchant_name="Zomato",
        fingerprint=f"fp-zomato-{uuid.uuid4().hex}",
    )
    db_session.add_all([t1, t2])
    db_session.flush()

    res = execute_query_transactions(
        db_session,
        test_user.id,
        QueryTransactionsInput(category_slug="food-dining", transaction_type="DEBIT"),
    )

    assert res["total_amount_inr"] == 1500.0
    assert res["transaction_count"] == 2
    assert res["average_amount_inr"] == 750.0
    assert len(res["top_merchants"]) == 2

# ============================================================================
# 3. Tenant User Isolation
# ============================================================================

def test_tenant_authorization_isolation(db_session: Session, test_user, test_account, test_categories):
    from app.models.user import User

    # Create User B
    user_b = User(
        email=f"user_b_{uuid.uuid4().hex[:6]}@finpilot.in",
        password_hash="hashed_pwd",
        full_name="User B",
        currency="INR",
        is_active=True,
    )
    db_session.add(user_b)
    db_session.flush()

    # User A transaction
    food_cat = test_categories["food-dining"]
    t_a = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=food_cat.id,
        date=date.today(),
        amount_paise=99900,
        transaction_type="DEBIT",
        narration="User A Secret Purchase",
        merchant_name="Secret Store",
        fingerprint=f"fp-secret-{uuid.uuid4().hex}",
    )
    db_session.add(t_a)
    db_session.flush()

    # User B queries transactions - must return zero!
    res_b = execute_query_transactions(
        db_session,
        user_b.id,
        QueryTransactionsInput(category_slug="food-dining", transaction_type="DEBIT"),
    )
    assert res_b["total_amount_inr"] == 0.0
    assert res_b["transaction_count"] == 0

# ============================================================================
# 4. Guardrails & Prompt Injection Defenses
# ============================================================================

def test_guardrails_sanitization_and_out_of_scope():
    # 1. Strips credentials & tokens
    raw = "My token is eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.t-ID and key is gsk_12345678901234567890123456"
    sanitized = sanitize_user_input(raw)
    assert "[REDACTED_TOKEN]" in sanitized
    assert "[REDACTED_API_KEY]" in sanitized

    # 2. Out of scope: money transfer
    transfer_query = "Transfer 50000 rupees to my friend right now"
    refusal = check_out_of_scope(transfer_query)
    assert refusal is not None
    assert "cannot execute fund transfers" in refusal.lower()

    # 3. Out of scope: speculative stock advice
    speculative_query = "Give me guaranteed multibagger stocks for 500% return"
    refusal = check_out_of_scope(speculative_query)
    assert refusal is not None
    assert "guarantee financial returns" in refusal.lower()

# ============================================================================
# 5. Conversation CRUD Endpoints
# ============================================================================

def test_conversation_crud_api(client: TestClient, auth_user: dict):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    # 1. Create conversation
    res = client.post("/api/v1/copilot/conversations", json={"title": "Q4 Financial Planning"}, headers=headers)
    assert res.status_code == 201
    conv_id = res.json()["id"]
    assert res.json()["title"] == "Q4 Financial Planning"

    # 2. List conversations
    res = client.get("/api/v1/copilot/conversations", headers=headers)
    assert res.status_code == 200
    assert any(c["id"] == conv_id for c in res.json())

    # 3. Rename conversation
    res = client.patch(f"/api/v1/copilot/conversations/{conv_id}", json={"title": "Updated Q4 Strategy"}, headers=headers)
    assert res.status_code == 200
    assert res.json()["title"] == "Updated Q4 Strategy"

    # 4. Get messages
    res = client.get(f"/api/v1/copilot/conversations/{conv_id}/messages", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1  # includes seeded welcome

    # 5. Delete conversation
    res = client.delete(f"/api/v1/copilot/conversations/{conv_id}", headers=headers)
    assert res.status_code == 204

# ============================================================================
# 6. Integration: Grounded Spending Question Uses Real Transactions
# ============================================================================

def test_copilot_spending_turn_uses_actual_transactions(
    client: TestClient,
    auth_user: dict,
    db_session: Session,
    test_categories: dict,
):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    # Find registered user in DB
    user_id = uuid.UUID(auth_user["user"]["id"])
    account = FinancialAccount(
        user_id=user_id,
        name="HDFC Salary",
        account_type="SAVINGS",
        institution="HDFC",
        balance_paise=15000000,
        currency="INR",
        is_active=True,
    )
    db_session.add(account)
    db_session.flush()

    # Seed actual food transactions
    food_cat = test_categories["food-dining"]
    tx1 = Transaction(
        user_id=user_id,
        account_id=account.id,
        category_id=food_cat.id,
        date=date.today(),
        amount_paise=125000,  # ₹1,250
        transaction_type="DEBIT",
        narration="Swiggy Gourmet",
        merchant_name="Swiggy",
        fingerprint=f"fp-swiggy-{uuid.uuid4().hex}",
    )
    tx2 = Transaction(
        user_id=user_id,
        account_id=account.id,
        category_id=food_cat.id,
        date=date.today(),
        amount_paise=75000,   # ₹750
        transaction_type="DEBIT",
        narration="Zomato Pizza",
        merchant_name="Zomato",
        fingerprint=f"fp-zomato-{uuid.uuid4().hex}",
    )
    db_session.add_all([tx1, tx2])
    db_session.flush()

    # Create conversation
    c_res = client.post("/api/v1/copilot/conversations", json={"title": "Dining Audit"}, headers=headers)
    conv_id = c_res.json()["id"]

    # Post question
    q_res = client.post(
        f"/api/v1/copilot/conversations/{conv_id}/messages",
        json={"query": "How much did I spend on food this month?"},
        headers=headers,
    )
    assert q_res.status_code == 200
    data = q_res.json()

    # Assert ground truth: ₹2,000.00 spent across 2 transactions!
    assert "₹2,000.00" in data["answer"]
    assert "2 transactions" in data["answer"]
    assert len(data["citations"]) >= 1
    assert data["citations"][0]["value"] == "₹2,000.00"
    assert len(data["suggested_followups"]) > 0

# ============================================================================
# 7. Integration: Affordability Scenario Simulation
# ============================================================================

def test_copilot_affordability_scenario(
    client: TestClient,
    auth_user: dict,
    db_session: Session,
):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}
    user_id = uuid.UUID(auth_user["user"]["id"])

    # Seed liquid balance
    acc = FinancialAccount(
        user_id=user_id,
        name="Axis Savings",
        account_type="SAVINGS",
        institution="Axis Bank",
        balance_paise=8500000,  # ₹85,000
        currency="INR",
        is_active=True,
    )
    db_session.add(acc)
    db_session.flush()

    c_res = client.post("/api/v1/copilot/conversations", json={"title": "Purchase Check"}, headers=headers)
    conv_id = c_res.json()["id"]

    res = client.post(
        f"/api/v1/copilot/conversations/{conv_id}/messages",
        json={"query": "Can I afford a ₹15,000 purchase without dropping below my emergency reserve?"},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["scenario_card"] is not None
    assert data["scenario_card"]["type"] == "AFFORDABILITY"
    assert data["scenario_card"]["verdict"] in ["AFFORDABLE_SAFE", "TEMPORARY_DIP_WARNING", "NOT_RECOMMENDED_DEFICIT"]
    assert "₹15,000" in data["answer"] or "₹15000" in data["answer"]
    assert len(data["citations"]) >= 1

# ============================================================================
# 8. Legacy Backwards Compatibility
# ============================================================================

def test_copilot_legacy_compatibility(client: TestClient, auth_user: dict):
    headers = {"Authorization": f"Bearer {auth_user['token']}"}

    # Test legacy /api/v1/copilot/history
    res = client.get("/api/v1/copilot/history", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)

    # Test legacy /api/v1/copilot/query
    res = client.post("/api/v1/copilot/query", json={"query": "What is my financial health score?"}, headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "answer" in data
    assert "citations" in data
    assert "suggested_followups" in data
