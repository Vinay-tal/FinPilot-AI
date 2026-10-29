from datetime import date
from fastapi.testclient import TestClient

def test_dashboard_summary_and_metrics(client: TestClient, auth_user: dict):
    headers = auth_user["headers"]
    today = date.today()

    # Create account
    acct = client.post("/api/v1/accounts", json={
        "name": "Main Checking",
        "institution": "HDFC",
        "balance_paise": 20000000,  # ₹2,00,000.00
    }, headers=headers).json()

    cats = client.get("/api/v1/categories", headers=headers).json()
    salary_cat = next(c for c in cats if c["slug"] == "salary")
    food_cat = next(c for c in cats if c["slug"] == "food-dining")

    # Inflow ₹1,00,000.00 (10000000 paise)
    client.post("/api/v1/transactions", json={
        "account_id": acct["id"],
        "category_id": salary_cat["id"],
        "date": today.isoformat(),
        "amount_paise": 10000000,
        "transaction_type": "CREDIT",
        "narration": "Monthly Salary",
    }, headers=headers)

    # Outflow ₹40,000.00 (4000000 paise)
    client.post("/api/v1/transactions", json={
        "account_id": acct["id"],
        "category_id": food_cat["id"],
        "date": today.isoformat(),
        "amount_paise": 4000000,
        "transaction_type": "DEBIT",
        "narration": "Dining Out",
    }, headers=headers)

    # Fetch summary
    summary_res = client.get("/api/v1/dashboard/summary?period=current_month", headers=headers)
    assert summary_res.status_code == 200
    summary = summary_res.json()

    assert summary["total_income_paise"] == 10000000
    assert summary["total_income_inr"] == 100000.0
    assert summary["total_expenses_paise"] == 4000000
    assert summary["total_expenses_inr"] == 40000.0
    assert summary["net_savings_paise"] == 6000000
    assert summary["net_savings_inr"] == 60000.0
    assert summary["savings_rate"] == 60.0  # 60% savings rate
    assert summary["accounts_count"] == 1
    assert summary["transactions_count"] == 2
    assert summary["health_score"] >= 70

    # Trend test
    trend_res = client.get("/api/v1/dashboard/cashflow-trend?months=6", headers=headers)
    assert trend_res.status_code == 200
    trend = trend_res.json()
    assert len(trend) == 6

    # Category breakdown test
    breakdown_res = client.get("/api/v1/dashboard/category-breakdown?period=current_month", headers=headers)
    assert breakdown_res.status_code == 200
    breakdown = breakdown_res.json()
    assert len(breakdown) == 1
    assert breakdown[0]["category_name"] == "Food & Dining"
    assert breakdown[0]["percentage"] == 100.0
