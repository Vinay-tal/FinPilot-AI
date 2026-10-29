import pytest
import uuid
from app.services.csv_import_service import (
    preview_csv_statement,
    execute_csv_import,
    generate_failed_rows_csv,
    parse_indian_date,
    detect_encoding,
)
from app.models.transaction import Transaction
from app.models.account import FinancialAccount

SAMPLE_HDFC_CSV = """Date,Narration,Chq./Ref.No.,Withdrawal Amount (INR ),Deposit Amount (INR ),Closing Balance
22/10/2026,SWIGGY FOOD ORDER,629104829102,450.00,,45230.50
23/10/2026,UBER RIDE BANGALORE,UBR2910283,280.00,,44950.50
24/10/2026,ZEPTO GROCERIES,ZPT928371,620.00,,44330.50
30/10/2026,ACH CR-INFOSYS-SALARY,INF202610,,125000.00,169330.50
"""

SAMPLE_CSV_WITH_ERRORS = """Date,Narration,Withdrawal,Deposit
22/10/2026,Valid Transaction,500.00,
invalid-date,Invalid Date Item,200.00,
23/10/2026,Zero Amount Item,0.00,
"""

def test_parse_indian_date_formats():
    assert str(parse_indian_date("22/10/2026")) == "2026-10-22"
    assert str(parse_indian_date("22-10-2026")) == "2026-10-22"
    assert str(parse_indian_date("2026-10-22")) == "2026-10-22"
    assert str(parse_indian_date("22-Oct-2026")) == "2026-10-22"
    assert parse_indian_date("invalid-date") is None

def test_csv_preview(db, test_user, test_account):
    file_bytes = SAMPLE_HDFC_CSV.encode("utf-8")
    preview = preview_csv_statement(
        file_bytes=file_bytes,
        filename="hdfc_stmt.csv",
        db=db,
        user_id=test_user.id,
        account_id=test_account.id,
        limit=5,
    )

    assert preview["filename"] == "hdfc_stmt.csv"
    assert "Date" in preview["columns"]
    assert preview["suggested_mapping"]["date_col"] == "Date"
    assert preview["suggested_mapping"]["narration_col"] == "Narration"
    assert preview["suggested_mapping"]["debit_col"] == "Withdrawal Amount (INR )"
    assert preview["suggested_mapping"]["credit_col"] == "Deposit Amount (INR )"
    assert len(preview["preview_rows"]) == 4
    assert preview["preview_rows"][0]["amount_inr"] == 450.00
    assert preview["preview_rows"][3]["amount_inr"] == 125000.00
    assert preview["preview_rows"][3]["transaction_type"] == "CREDIT"

def test_csv_import_execution_and_balance_adjustment(db, test_user, test_account):
    initial_balance_paise = test_account.balance_paise
    file_bytes = SAMPLE_HDFC_CSV.encode("utf-8")

    mapping = {
        "date_col": "Date",
        "narration_col": "Narration",
        "debit_col": "Withdrawal Amount (INR )",
        "credit_col": "Deposit Amount (INR )",
        "ref_col": "Chq./Ref.No.",
    }

    result = execute_csv_import(
        file_bytes=file_bytes,
        filename="hdfc_stmt.csv",
        account_id=test_account.id,
        user_id=test_user.id,
        column_mapping=mapping,
        db=db,
        bank_format="HDFC",
    )

    assert result["status"] == "COMPLETED"
    assert result["imported_rows"] == 4
    assert result["duplicate_rows"] == 0
    assert result["failed_rows_count"] == 0

    # Net change: -450 - 280 - 620 + 125000 = +123,650 INR = +12365000 paise
    db.refresh(test_account)
    expected_balance = initial_balance_paise + 12365000
    assert test_account.balance_paise == expected_balance

def test_safe_duplicate_reimport(db, test_user, test_account):
    file_bytes = SAMPLE_HDFC_CSV.encode("utf-8")
    mapping = {
        "date_col": "Date",
        "narration_col": "Narration",
        "debit_col": "Withdrawal Amount (INR )",
        "credit_col": "Deposit Amount (INR )",
        "ref_col": "Chq./Ref.No.",
    }

    # First import
    res1 = execute_csv_import(
        file_bytes=file_bytes,
        filename="hdfc_stmt.csv",
        account_id=test_account.id,
        user_id=test_user.id,
        column_mapping=mapping,
        db=db,
        bank_format="HDFC",
    )
    balance_after_first = test_account.balance_paise

    # Second import with the EXACT same file
    res2 = execute_csv_import(
        file_bytes=file_bytes,
        filename="hdfc_stmt.csv",
        account_id=test_account.id,
        user_id=test_user.id,
        column_mapping=mapping,
        db=db,
        bank_format="HDFC",
    )

    assert res2["status"] == "COMPLETED"
    assert res2["imported_rows"] == 0
    assert res2["duplicate_rows"] == 4

    # Balance must NOT change on re-import
    db.refresh(test_account)
    assert test_account.balance_paise == balance_after_first

def test_csv_import_with_row_errors(db, test_user, test_account):
    file_bytes = SAMPLE_CSV_WITH_ERRORS.encode("utf-8")
    mapping = {
        "date_col": "Date",
        "narration_col": "Narration",
        "debit_col": "Withdrawal",
        "credit_col": "Deposit",
    }

    result = execute_csv_import(
        file_bytes=file_bytes,
        filename="errors_stmt.csv",
        account_id=test_account.id,
        user_id=test_user.id,
        column_mapping=mapping,
        db=db,
        bank_format="GENERIC",
    )

    assert result["status"] == "COMPLETED"
    assert result["imported_rows"] == 1
    assert result["failed_rows_count"] == 2
    assert "Invalid date format" in result["failed_rows"][0]["reason"]

    # Verify downloadable CSV error report
    err_csv = generate_failed_rows_csv(result["failed_rows"])
    assert "Row Number" in err_csv
    assert "Invalid date format" in err_csv
