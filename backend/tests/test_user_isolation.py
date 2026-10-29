from datetime import date
from fastapi.testclient import TestClient

def test_cross_tenant_isolation(client: TestClient, auth_user: dict, second_auth_user: dict):
    headers_a = auth_user["headers"]
    headers_b = second_auth_user["headers"]
    today = date.today()

    # --- User A creates resources ---
    # 1. User A creates Account
    acct_a_res = client.post("/api/v1/accounts", json={
        "name": "User A Private Account",
        "institution": "Axis Bank",
        "balance_paise": 10000000,
    }, headers=headers_a)
    acct_a_id = acct_a_res.json()["id"]

    # 2. User A creates Transaction
    cats = client.get("/api/v1/categories", headers=headers_a).json()
    food_cat = next(c for c in cats if c["slug"] == "food-dining")
    tx_a_res = client.post("/api/v1/transactions", json={
        "account_id": acct_a_id,
        "category_id": food_cat["id"],
        "date": today.isoformat(),
        "amount_paise": 250000,
        "transaction_type": "DEBIT",
        "narration": "Confidential User A Purchase",
    }, headers=headers_a)
    tx_a_id = tx_a_res.json()["id"]

    # 3. User A creates Budget
    budget_a_res = client.post("/api/v1/budgets", json={
        "category_id": food_cat["id"],
        "month": today.month,
        "year": today.year,
        "amount_paise": 5000000,
    }, headers=headers_a)
    budget_a_id = budget_a_res.json()["id"]

    # 4. User A creates Goal
    goal_a_res = client.post("/api/v1/goals", json={
        "name": "User A Secret Goal",
        "target_amount_paise": 50000000,
        "target_date": "2027-01-01",
    }, headers=headers_a)
    goal_a_id = goal_a_res.json()["id"]

    # --- User B attempts unauthorized access to User A's resources ---

    # 1. Account Isolation
    assert client.get(f"/api/v1/accounts/{acct_a_id}", headers=headers_b).status_code == 403
    assert client.put(f"/api/v1/accounts/{acct_a_id}", json={"name": "Hacked"}, headers=headers_b).status_code == 403
    assert client.delete(f"/api/v1/accounts/{acct_a_id}", headers=headers_b).status_code == 403
    # User B account listing must not contain User A's account
    user_b_accounts = client.get("/api/v1/accounts", headers=headers_b).json()
    assert len(user_b_accounts) == 0

    # 2. Transaction Isolation
    assert client.get(f"/api/v1/transactions/{tx_a_id}", headers=headers_b).status_code == 403
    assert client.delete(f"/api/v1/transactions/{tx_a_id}", headers=headers_b).status_code == 403
    # User B transaction listing must be empty
    user_b_txs = client.get("/api/v1/transactions", headers=headers_b).json()
    assert user_b_txs["total"] == 0
    assert len(user_b_txs["items"]) == 0

    # 3. Budget Isolation
    assert client.put(f"/api/v1/budgets/{budget_a_id}", json={"amount_paise": 100}, headers=headers_b).status_code == 403
    assert client.delete(f"/api/v1/budgets/{budget_a_id}", headers=headers_b).status_code == 403
    # User B budget listing must have 0 budgets
    user_b_budgets = client.get(f"/api/v1/budgets?month={today.month}&year={today.year}", headers=headers_b).json()
    assert len(user_b_budgets) == 0

    # 4. Goal Isolation
    assert client.get(f"/api/v1/goals/{goal_a_id}", headers=headers_b).status_code == 403
    assert client.put(f"/api/v1/goals/{goal_a_id}", json={"name": "Hacked Goal"}, headers=headers_b).status_code == 403
    assert client.delete(f"/api/v1/goals/{goal_a_id}", headers=headers_b).status_code == 403
    # User B goals listing must be empty
    user_b_goals = client.get("/api/v1/goals", headers=headers_b).json()
    assert len(user_b_goals) == 0

    # 5. Dashboard Summary Isolation
    user_b_summary = client.get("/api/v1/dashboard/summary?period=current_month", headers=headers_b).json()
    assert user_b_summary["total_income_paise"] == 0
    assert user_b_summary["total_expenses_paise"] == 0
    assert user_b_summary["accounts_count"] == 0
    assert user_b_summary["transactions_count"] == 0
