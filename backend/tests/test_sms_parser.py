import pytest
from app.services.sms_parser_service import get_sms_parser, RegexBankSMSParser

def test_hdfc_debit_sms_parsing():
    parser = get_sms_parser()
    sms = "Dear Customer, INR 850.00 has been debited from your HDFC Bank A/C ending XX1829 on 22-OCT-26 to SWIGGY. Info: UPI/629104829102. Avail Bal: INR 45,230.50."
    res = parser.parse(sms)

    assert res.success is True
    assert res.bank_name == "HDFC"
    assert res.transaction_type == "DEBIT"
    assert res.amount_inr == 850.00
    assert res.amount_paise == 85000
    assert res.account_mask == "1829"
    assert res.merchant_name == "Swiggy"
    assert res.reference_id == "629104829102"
    assert res.available_balance_inr == 45230.50
    assert res.available_balance_paise == 4523050

def test_icici_credit_salary_sms_parsing():
    parser = get_sms_parser()
    sms = "Acct XX4920 credited with INR 1,25,000.00 on 30-Oct-26 by INFOSYS TECH SALARY. Avail Bal INR 1,87,410.00."
    res = parser.parse(sms)

    assert res.success is True
    assert res.transaction_type == "CREDIT"
    assert res.amount_inr == 125000.00
    assert res.amount_paise == 12500000
    assert res.account_mask == "4920"
    assert res.merchant_name == "Employer Payroll"
    assert res.available_balance_inr == 187410.00

def test_sbi_utility_bill_sms_parsing():
    parser = get_sms_parser()
    sms = "SBI: Your A/C XX9876 has a debit by transfer of Rs 450.00 on 22/10/26 towards BESCOM. Ref No 628192739182. Bal Rs 12,340.20."
    res = parser.parse(sms)

    assert res.success is True
    assert res.bank_name == "SBI"
    assert res.transaction_type == "DEBIT"
    assert res.amount_inr == 450.00
    assert res.merchant_name == "Electricity Board"
    assert res.reference_id == "628192739182"
    assert res.available_balance_inr == 12340.20

def test_axis_credit_card_sms_parsing():
    parser = get_sms_parser()
    sms = "Alert: You have spent INR 3,499.00 on Axis Bank Card ending 4410 at AMAZON PAY on 22-10-2026. Avail Limit: INR 1,46,501.00."
    res = parser.parse(sms)

    assert res.success is True
    assert res.bank_name == "AXIS"
    assert res.account_type == "CREDIT_CARD"
    assert res.account_mask == "4410"
    assert res.amount_inr == 3499.00
    assert res.merchant_name == "Amazon"
    assert res.transaction_type == "DEBIT"

def test_phonepe_upi_receipt_sms_parsing():
    parser = get_sms_parser()
    sms = "Paid Rs. 150 to CHAI POINT via UPI Ref No 629102938471 on 22 Oct 2026."
    res = parser.parse(sms)

    assert res.success is True
    assert res.amount_inr == 150.00
    assert res.transaction_type == "DEBIT"
    assert res.merchant_name == "Chai Point"
    assert res.reference_id == "629102938471"

def test_refund_sms_parsing():
    parser = get_sms_parser()
    sms = "Refund of INR 520.00 credited to your A/C XX1829 on 21-Oct-26 for cancelled Zomato order. Ref 928371928374."
    res = parser.parse(sms)

    assert res.success is True
    assert res.transaction_type == "CREDIT"
    assert res.amount_inr == 520.00
    assert res.merchant_name == "Zomato"

def test_malformed_sms_fails_gracefully():
    parser = get_sms_parser()
    res = parser.parse("Good morning! Enjoy 20% off on your next purchase using code SAVE20.")
    assert res.success is False
    assert res.amount_inr == 0.0
    assert "amount" in res.error.lower()
