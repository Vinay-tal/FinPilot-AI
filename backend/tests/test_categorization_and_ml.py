import pytest
from app.services.categorization_service import (
    normalize_merchant,
    categorize_transaction,
    record_user_correction,
)
from app.ml.classifier import TransactionClassifier, clean_text_for_ml
from app.ml.dataset import SAMPLE_TRAINING_DATA

def test_merchant_normalization():
    assert normalize_merchant("SWIGGY*INDIRANAGAR BANGALORE") == "Swiggy"
    assert normalize_merchant("UBER * TRIP BANGALORE KA") == "Uber"
    assert normalize_merchant("ZOMATO RESTAURANT ORDER 92837") == "Zomato"
    assert normalize_merchant("BLINKIT INSTANT DELIVERY") == "Blinkit"
    assert normalize_merchant("BESCOM ELECTRICITY BILL BANGALORE") == "Electricity Board"
    assert normalize_merchant("AMAZON PAY INDIA MUMBAI") == "Amazon"
    assert normalize_merchant("NETFLIX.COM MONTHLY") == "Netflix"
    assert normalize_merchant("ZERODHA BROKING LTD INFLOW") == "Zerodha"

def test_rule_categorization_priority():
    # 1. Salary Credit
    salary_res = categorize_transaction("ACH CR-INFOSYS TECH LTD-SALARY-OCT26", tx_type="CREDIT")
    assert salary_res["category_slug"] == "salary"
    assert salary_res["method"] == "RULE"
    assert salary_res["confidence"] >= 0.95

    # 2. Refund
    refund_res = categorize_transaction("REFUND CREDITED VIA UPI AMAZON PAY", tx_type="CREDIT")
    assert refund_res["category_slug"] == "refunds-cashback"
    assert refund_res["method"] == "RULE"

    # 3. Known merchant
    swiggy_res = categorize_transaction("SWIGGY FOOD DELIVERY", tx_type="DEBIT")
    assert swiggy_res["category_slug"] == "food-dining"
    assert swiggy_res["merchant_name"] == "Swiggy"
    assert swiggy_res["method"] == "RULE"

def test_ml_categorization_and_confidence():
    clf = TransactionClassifier(model_version="test_v1")
    clf.train_and_evaluate(data=SAMPLE_TRAINING_DATA, test_size=0.20)

    # Test predictions on unseen variations
    cat, conf = clf.predict("Coursera course deep learning specialization")
    assert cat == "education"
    assert conf > 0.15

    cat2, conf2 = clf.predict("Decathlon sports running shoes store")
    assert cat2 == "shopping-lifestyle"
    assert conf2 > 0.15

def test_text_cleaning_preprocessing():
    cleaned = clean_text_for_ml("UPI/zepto.fresh@hdfcbank/Zepto Groceries 2026-10-22 Ref 019283749281")
    assert "upi" not in cleaned
    assert "2026" not in cleaned
    assert "019283749281" not in cleaned
    assert "zepto" in cleaned
    assert "groceries" in cleaned

def test_model_evaluation_metrics_validity():
    clf = TransactionClassifier(model_version="test_eval")
    metrics = clf.train_and_evaluate(data=SAMPLE_TRAINING_DATA, test_size=0.20)

    assert "accuracy" in metrics
    assert "macro_f1" in metrics
    assert "classes" in metrics
    assert metrics["macro_f1"] > 0.65
    assert metrics["total_samples"] == len(SAMPLE_TRAINING_DATA)
    assert metrics["train_samples"] + metrics["test_samples"] == len(SAMPLE_TRAINING_DATA)

def test_user_correction_immutability(db, test_user, test_account, test_categories):
    from app.models.transaction import Transaction
    from datetime import date

    misc_cat = test_categories["miscellaneous"]
    food_cat = test_categories["food-dining"]

    tx = Transaction(
        user_id=test_user.id,
        account_id=test_account.id,
        category_id=misc_cat.id,
        date=date.today(),
        amount_paise=45000,
        transaction_type="DEBIT",
        narration="Custom Mystery Cafe",
        fingerprint="test_fp_user_corr",
        categorization_method="ML",
        categorization_confidence=0.45,
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)

    # User reclassifies transaction
    updated = record_user_correction(
        db=db,
        transaction_id=str(tx.id),
        new_category_id=str(food_cat.id),
        user_id=str(test_user.id),
    )

    assert updated.category_id == food_cat.id
    assert updated.categorization_method == "MANUAL"
    assert updated.categorization_confidence == 1.0
