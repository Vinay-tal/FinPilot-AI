from datetime import date
from fastapi.testclient import TestClient

def test_transaction_creation_and_balance_update(client: TestClient, auth_user: dict):
    headers = auth_user["headers"]

    # 1. Create account with opening balance ₹10,000 (1000000 paise)
    acct_res = client.post("/api/v1/accounts", json={
        "name": "Test Bank A/C",
        "account_type": "SAVINGS",
        "institution": "SBI",
        "balance_paise": 1000000,
    }, headers=headers)
    acct_id = acct_res.json()["id"]

    # 2. Get category ID for Food & Dining
    cats = client.get("/api/v1/categories", headers=headers).json()
    food_cat = next(c for c in cats if c["slug"] == "food-dining")
    salary_cat = next(c for c in cats if c["slug"] == "salary")

    # 3. Create Debit Transaction (-₹550.00 = 55000 paise)
    debit_tx_payload = {
        "account_id": acct_id,
        "category_id": food_cat["id"],
        "date": date.today().isoformat(),
        "amount_paise": 55000,
        "transaction_type": "DEBIT",
        "narration": "UPI-SWIGGY-BANGALORE",
        "merchant_name": "Swiggy",
        "payment_mode": "UPI",
    }
    tx_res = client.post("/api/v1/transactions", json=debit_tx_payload, headers=headers)
    assert tx_res.status_code == 201
    tx = tx_res.json()
    assert tx["amount_paise"] == 55000
    assert tx["amount_inr"] == 550.0
    assert tx["category_name"] == "Food & Dining"

    # Verify Account balance decreased to ₹9,450.00 (945000 paise)
    acct_check = client.get(f"/api/v1/accounts/{acct_id}", headers=headers).json()
    assert acct_check["balance_paise"] == 945000

    # 4. Create Credit Transaction (+₹50,000.00 = 5000000 paise)
    credit_tx_payload = {
        "account_id": acct_id,
        "category_id": salary_cat["id"],
        "date": date.today().isoformat(),
        "amount_paise": 5000000,
        "transaction_type": "CREDIT",
        "narration": "ACH SALARY CREDIT",
        "payment_mode": "NET_BANKING",
    }
    client.post("/api/v1/transactions", json=credit_tx_payload, headers=headers)

    # Verify Account balance increased to ₹59,450.00 (5945000 paise)
    acct_check_2 = client.get(f"/api/v1/accounts/{acct_id}", headers=headers).json()
    assert acct_check_2["balance_paise"] == 5945000

    # 5. Duplicate transaction detection test
    dup_res = client.post("/api/v1/transactions", json=debit_tx_payload, headers=headers)
    assert dup_res.status_code == 409
    assert dup_res.json()["error_code"] == "RESOURCE_CONFLICT"

def test_transaction_filtering_and_pagination(client: TestClient, auth_user: dict):
    headers = auth_user["headers"]

    acct_res = client.post("/api/v1/accounts", json={
        "name": "SBI Savings",
        "account_type": "SAVINGS",
        "institution": "SBI",
        "balance_paise": 5000000,
    }, headers=headers)
    acct_id = acct_res.json()["id"]

    cats = client.get("/api/v1/categories", headers=headers).json()
    food_cat = next(c for c in cats if c["slug"] == "food-dining")
    travel_cat = next(c for c in cats if c["slug"] == "transportation-fuel")

    # Insert 3 transactions
    client.post("/api/v1/transactions", json={
        "account_id": acct_id,
        "category_id": food_cat["id"],
        "date": "2026-10-01",
        "amount_paise": 45000,
        "transaction_type": "DEBIT",
        "narration": "Swiggy Indiranagar",
        "merchant_name": "Swiggy",
    }, headers=headers)

    client.post("/api/v1/transactions", json={
        "account_id": acct_id,
        "category_id": food_cat["id"],
        "date": "2026-10-05",
        "amount_paise": 72000,
        "transaction_type": "DEBIT",
        "narration": "Zomato Koramangala",
        "merchant_name": "Zomato",
    }, headers=headers)

    client.post("/api/v1/transactions", json={
        "account_id": acct_id,
        "category_id": travel_cat["id"],
        "date": "2026-10-10",
        "amount_paise": 31000,
        "transaction_type": "DEBIT",
        "narration": "Uber Ride to Airport",
        "merchant_name": "Uber",
    }, headers=headers)

    # Test pagination: page 1, limit 2
    p1 = client.get("/api/v1/transactions?page=1&limit=2", headers=headers).json()
    assert len(p1["items"]) == 2
    assert p1["total"] == 3
    assert p1["total_pages"] == 2

    # Test category filter
    food_res = client.get(f"/api/v1/transactions?category_id={food_cat['id']}", headers=headers).json()
    assert food_res["total"] == 2

    # Test text search
    search_res = client.get("/api/v1/transactions?search=uber", headers=headers).json()
    assert search_res["total"] == 1
    assert search_res["items"][0]["merchant_name"] == "Uber"
