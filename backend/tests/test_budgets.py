from datetime import date
from fastapi.testclient import TestClient

def test_budget_pacing_and_crud(client: TestClient, auth_user: dict):
    headers = auth_user["headers"]
    today = date.today()

    cats = client.get("/api/v1/categories", headers=headers).json()
    food_cat = next(c for c in cats if c["slug"] == "food-dining")

    # 1. Create monthly budget of ₹10,000.00 (1000000 paise)
    create_payload = {
        "category_id": food_cat["id"],
        "month": today.month,
        "year": today.year,
        "amount_paise": 1000000,
        "alert_threshold": 0.80,
    }
    b_res = client.post("/api/v1/budgets", json=create_payload, headers=headers)
    assert b_res.status_code == 201
    budget = b_res.json()
    b_id = budget["id"]
    assert budget["amount_paise"] == 1000000
    assert budget["amount_inr"] == 10000.0
    assert budget["alert_status"] == "NORMAL"

    # 2. Duplicate monthly budget should fail
    dup_res = client.post("/api/v1/budgets", json=create_payload, headers=headers)
    assert dup_res.status_code == 409

    # 3. Create account and debit transaction to test spend actuals
    acct_res = client.post("/api/v1/accounts", json={
        "name": "Checking",
        "institution": "Bank",
        "balance_paise": 5000000
    }, headers=headers)
    acct_id = acct_res.json()["id"]

    # Spend ₹8,500.00 (850000 paise) - triggers 85% (>80% threshold => WARNING)
    client.post("/api/v1/transactions", json={
        "account_id": acct_id,
        "category_id": food_cat["id"],
        "date": today.isoformat(),
        "amount_paise": 850000,
        "transaction_type": "DEBIT",
        "narration": "Large Family Dinner",
    }, headers=headers)

    # 4. List budgets and verify pacing actuals
    list_res = client.get(f"/api/v1/budgets?month={today.month}&year={today.year}", headers=headers)
    assert list_res.status_code == 200
    budgets = list_res.json()
    assert len(budgets) == 1
    b_check = budgets[0]
    assert b_check["spent_paise"] == 850000
    assert b_check["spent_inr"] == 8500.0
    assert b_check["remaining_paise"] == 150000
    assert b_check["remaining_inr"] == 1500.0
    assert b_check["pacing_pct"] == 85.0
    assert b_check["alert_status"] == "WARNING"

    # 5. Delete budget
    del_res = client.delete(f"/api/v1/budgets/{b_id}", headers=headers)
    assert del_res.status_code == 204
