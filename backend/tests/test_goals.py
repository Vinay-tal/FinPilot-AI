from datetime import date
from fastapi.testclient import TestClient

def test_savings_goals_crud(client: TestClient, auth_user: dict):
    headers = auth_user["headers"]

    # 1. Create Goal
    payload = {
        "name": "Emergency Fund 3-Month",
        "target_amount_paise": 15000000,  # ₹1,50,000.00
        "current_amount_paise": 7500000,   # ₹75,000.00 (50%)
        "target_date": "2026-12-31",
        "category": "EMERGENCY_FUND",
        "priority": "HIGH",
    }
    create_res = client.post("/api/v1/goals", json=payload, headers=headers)
    assert create_res.status_code == 201
    goal = create_res.json()
    assert goal["progress_pct"] == 50.0
    assert goal["target_amount_inr"] == 150000.0
    assert goal["current_amount_inr"] == 75000.0
    goal_id = goal["id"]

    # 2. Update Goal towards completion
    update_res = client.put(f"/api/v1/goals/{goal_id}", json={
        "current_amount_paise": 15000000
    }, headers=headers)
    assert update_res.status_code == 200
    updated = update_res.json()
    assert updated["progress_pct"] == 100.0
    assert updated["status"] == "COMPLETED"

    # 3. Delete Goal
    del_res = client.delete(f"/api/v1/goals/{goal_id}", headers=headers)
    assert del_res.status_code == 204
