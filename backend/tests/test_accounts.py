from fastapi.testclient import TestClient

def test_account_crud(client: TestClient, auth_user: dict):
    headers = auth_user["headers"]

    # 1. Create Account
    payload = {
        "name": "HDFC Salary Account",
        "account_type": "SAVINGS",
        "institution": "HDFC Bank",
        "account_number_mask": "*4821",
        "balance_paise": 5000000,  # ₹50,000.00
        "currency": "INR",
    }
    create_res = client.post("/api/v1/accounts", json=payload, headers=headers)
    assert create_res.status_code == 201
    acct = create_res.json()
    assert acct["name"] == "HDFC Salary Account"
    assert acct["balance_paise"] == 5000000
    assert acct["balance_inr"] == 50000.0
    acct_id = acct["id"]

    # 2. List Accounts
    list_res = client.get("/api/v1/accounts", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["id"] == acct_id

    # 3. Get Single Account
    get_res = client.get(f"/api/v1/accounts/{acct_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "HDFC Salary Account"

    # 4. Update Account
    update_res = client.put(f"/api/v1/accounts/{acct_id}", json={"name": "HDFC Premium Salary A/C"}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "HDFC Premium Salary A/C"

    # 5. Delete Account
    del_res = client.delete(f"/api/v1/accounts/{acct_id}", headers=headers)
    assert del_res.status_code == 204

    # Verify deleted account is no longer in active list
    relist_res = client.get("/api/v1/accounts", headers=headers)
    assert len(relist_res.json()) == 0
