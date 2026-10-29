import pytest
from datetime import date, timedelta
from app.services.intelligence_service import (
    detect_recurring_patterns,
    detect_near_duplicate_warnings,
    detect_unusual_spending_anomalies,
    get_merchant_spending_summaries,
)
from app.models.transaction import Transaction

def test_detect_recurring_payments(db, test_user, test_account, test_categories):
    housing_cat = test_categories["housing-rent"]

    # Insert 3 monthly rent payments exactly 30 days apart
    d1 = date(2026, 7, 1)
    d2 = date(2026, 7, 31)
    d3 = date(2026, 8, 30)

    for i, d in enumerate([d1, d2, d3]):
        tx = Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=housing_cat.id,
            date=d,
            amount_paise=2800000,
            transaction_type="DEBIT",
            narration=f"Rent Payment Month {i+1}",
            merchant_name="Landlord Ramesh",
            fingerprint=f"rent_fp_{i}",
        )
        db.add(tx)
    db.commit()

    recurring = detect_recurring_patterns(db, test_user.id, lookback_days=180)
    assert len(recurring) >= 1
    found = [r for r in recurring if r["merchant_name"] == "Landlord Ramesh"][0]
    assert found["frequency"] == "MONTHLY"
    assert found["expected_amount_inr"] == 28000.00
    assert found["occurrences"] == 3

def test_detect_near_duplicates(db, test_user, test_account, test_categories):
    food_cat = test_categories["food-dining"]
    today = date.today()

    # Two identical transactions on the same day (double payment)
    tx1 = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=food_cat.id,
        date=today,
        amount_paise=45000,
        transaction_type="DEBIT",
        narration="Swiggy Order Biryani",
        merchant_name="Swiggy",
        fingerprint="swiggy_dup_1",
    )
    tx2 = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=food_cat.id,
        date=today,
        amount_paise=45000,
        transaction_type="DEBIT",
        narration="Swiggy Order Biryani (Retry)",
        merchant_name="Swiggy",
        fingerprint="swiggy_dup_2",
    )
    db.add_all([tx1, tx2])
    db.commit()

    warnings = detect_near_duplicate_warnings(db, test_user.id)
    assert len(warnings) >= 1
    assert warnings[0]["amount_inr"] == 450.00
    assert "Swiggy" in warnings[0]["merchant"]

def test_unusual_spending_iqr_anomaly(db, test_user, test_account, test_categories):
    food_cat = test_categories["food-dining"]

    # Insert 10 regular dining transactions around ₹300 - ₹500
    for i in range(10):
        amt = 35000 + (i * 2000)
        tx = Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=food_cat.id,
            date=date.today() - timedelta(days=i * 3),
            amount_paise=amt,
            transaction_type="DEBIT",
            narration=f"Regular Lunch {i}",
            merchant_name="Lunch Cafe",
            fingerprint=f"regular_lunch_{i}",
        )
        db.add(tx)

    # Insert 1 massive outlier: ₹15,000 fine dining
    outlier = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=food_cat.id,
        date=date.today(),
        amount_paise=1500000,
        transaction_type="DEBIT",
        narration="Luxury Fine Dining Celebration",
        merchant_name="Five Star Luxury Hotel",
        fingerprint="outlier_dinner",
    )
    db.add(outlier)
    db.commit()

    anomalies = detect_unusual_spending_anomalies(db, test_user.id, lookback_days=60)
    assert len(anomalies) >= 1
    found = [a for a in anomalies if a["transaction_id"] == str(outlier.id)][0]
    assert found["amount_inr"] == 15000.00
    assert found["severity"] == "CRITICAL"
    assert found["fold_increase"] > 5.0

def test_merchant_spending_summaries(db, test_user, test_account, test_categories):
    shop_cat = test_categories["shopping-lifestyle"]

    for i in range(4):
        tx = Transaction(
            user_id=test_user.id,
            account_id=test_account.id,
            category_id=shop_cat.id,
            date=date.today() - timedelta(days=i * 10),
            amount_paise=100000,
            transaction_type="DEBIT",
            narration=f"Amazon Order {i}",
            merchant_name="Amazon India",
            fingerprint=f"amzn_test_{i}",
        )
        db.add(tx)
    db.commit()

    summaries = get_merchant_spending_summaries(db, test_user.id, limit=5)
    assert len(summaries) >= 1
    amzn = [s for s in summaries if s["merchant_name"] == "Amazon India"][0]
    assert amzn["total_spent_inr"] == 4000.00
    assert amzn["transaction_count"] == 4
    assert amzn["avg_ticket_size_inr"] == 1000.00
