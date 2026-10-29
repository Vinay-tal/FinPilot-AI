import io
import csv
import json
import uuid
import hashlib
from datetime import datetime, date
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from sqlalchemy.orm import Session
from app.models.account import FinancialAccount
from app.models.category import TransactionCategory
from app.models.transaction import Transaction
from app.models.import_job import ImportJob
from app.services.transaction_service import compute_fingerprint
from app.services.categorization_service import categorize_transaction, normalize_merchant

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

COMMON_BANK_PRESETS = {
    "HDFC": {
        "date_col": "Date",
        "narration_col": "Narration",
        "debit_col": "Withdrawal Amount (INR )",
        "credit_col": "Deposit Amount (INR )",
        "balance_col": "Closing Balance",
        "ref_col": "Chq./Ref.No.",
    },
    "ICICI": {
        "date_col": "Transaction Date",
        "narration_col": "Transaction Remarks",
        "debit_col": "Withdrawal Amount (INR )",
        "credit_col": "Deposit Amount (INR )",
        "balance_col": "Balance (INR )",
        "ref_col": "Cheque Number",
    },
    "SBI": {
        "date_col": "Txn Date",
        "narration_col": "Description",
        "debit_col": "Debit",
        "credit_col": "Credit",
        "balance_col": "Balance",
        "ref_col": "Ref No./Cheque No.",
    },
    "AXIS": {
        "date_col": "Tran Date",
        "narration_col": "PARTICULARS",
        "debit_col": "DR",
        "credit_col": "CR",
        "balance_col": "BAL",
        "ref_col": "CHQNO",
    },
    "GENERIC": {
        "date_col": "date",
        "narration_col": "narration",
        "debit_col": "debit",
        "credit_col": "credit",
        "amount_col": "amount",
        "type_col": "type",
        "balance_col": "balance",
        "ref_col": "reference_id",
    },
}

def detect_encoding(raw_bytes: bytes) -> str:
    """Detect CSV file encoding safely with common fallbacks."""
    for enc in ["utf-8-sig", "utf-8", "latin-1", "cp1252"]:
        try:
            raw_bytes.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"

def parse_indian_date(date_str: str) -> Optional[date]:
    """Parse various Indian banking date formats into date object."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    formats = [
        "%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d-%m-%y",
        "%d-%b-%Y", "%d-%b-%y", "%d %b %Y", "%d %B %Y",
        "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            if dt.year < 2000:
                dt = dt.replace(year=dt.year + 100)
            return dt.date()
        except ValueError:
            continue
    return None

def parse_currency_amount(val: Any) -> float:
    """Parse string/number currency amount safely into float INR."""
    if val is None or pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val).strip().replace(",", "").replace("₹", "").replace("INR", "").replace("Rs.", "").strip()
    if not s or s == "-":
        return 0.0
    try:
        return abs(float(s))
    except ValueError:
        return 0.0

def infer_column_mapping(columns: List[str]) -> Dict[str, Optional[str]]:
    """Automatically suggest column mappings based on CSV headers."""
    cols_lower = {c.strip().lower(): c for c in columns}

    mapping = {
        "date_col": None,
        "narration_col": None,
        "debit_col": None,
        "credit_col": None,
        "amount_col": None,
        "type_col": None,
        "balance_col": None,
        "ref_col": None,
    }

    # Date
    for k in ["date", "txn date", "transaction date", "tran date", "value date", "posting date"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["date_col"] = orig
                break
        if mapping["date_col"]:
            break

    # Narration / Description
    for k in ["narration", "description", "particulars", "remarks", "transaction remarks", "details"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["narration_col"] = orig
                break
        if mapping["narration_col"]:
            break

    # Debit
    for k in ["withdrawal", "debit", "dr", "withdrawal amount"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["debit_col"] = orig
                break
        if mapping["debit_col"]:
            break

    # Credit
    for k in ["deposit", "credit", "cr", "deposit amount"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["credit_col"] = orig
                break
        if mapping["credit_col"]:
            break

    # Amount (single column)
    if not mapping["debit_col"] and not mapping["credit_col"]:
        for k in ["amount", "txn amount", "transaction amount", "net amount"]:
            for col_l, orig in cols_lower.items():
                if k in col_l:
                    mapping["amount_col"] = orig
                    break
            if mapping["amount_col"]:
                break

    # Type
    for k in ["type", "txn type", "cr/dr", "transaction type"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["type_col"] = orig
                break
        if mapping["type_col"]:
            break

    # Balance
    for k in ["balance", "closing balance", "avail bal", "bal"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["balance_col"] = orig
                break
        if mapping["balance_col"]:
            break

    # Reference
    for k in ["ref", "chq", "cheque", "utr", "reference", "ref no"]:
        for col_l, orig in cols_lower.items():
            if k in col_l:
                mapping["ref_col"] = orig
                break
        if mapping["ref_col"]:
            break

    return mapping

def preview_csv_statement(
    file_bytes: bytes,
    filename: str,
    db: Session,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    limit: int = 5,
) -> Dict[str, Any]:
    """Parse CSV headers, suggest mappings, and preview first rows with duplicate checks."""
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB")

    # Verify account belongs to authenticated user
    account = db.query(FinancialAccount).filter(
        FinancialAccount.id == account_id,
        FinancialAccount.user_id == user_id,
    ).first()
    if not account:
        raise ValueError("Invalid account or account does not belong to user.")

    encoding = detect_encoding(file_bytes)
    text = file_bytes.decode(encoding)

    # Read CSV via pandas
    df = pd.read_csv(io.StringIO(text), nrows=limit + 10)
    columns = list(df.columns)
    suggested_mapping = infer_column_mapping(columns)

    preview_rows: List[Dict[str, Any]] = []
    date_col = suggested_mapping.get("date_col")
    narration_col = suggested_mapping.get("narration_col")
    debit_col = suggested_mapping.get("debit_col")
    credit_col = suggested_mapping.get("credit_col")
    amount_col = suggested_mapping.get("amount_col")

    # Fetch existing fingerprints for this user to identify duplicates in preview
    existing_fingerprints = set(
        f[0] for f in db.query(Transaction.fingerprint).filter(Transaction.user_id == user_id).all()
    )

    for idx, row in df.head(limit).iterrows():
        raw_date = str(row[date_col]) if date_col and date_col in row else None
        parsed_d = parse_indian_date(raw_date) if raw_date else None
        narration = str(row[narration_col]).strip() if narration_col and narration_col in row else f"Row {idx+1}"

        debit_amt = parse_currency_amount(row[debit_col]) if debit_col and debit_col in row else 0.0
        credit_amt = parse_currency_amount(row[credit_col]) if credit_col and credit_col in row else 0.0

        if debit_amt > 0:
            tx_type = "DEBIT"
            amount_inr = debit_amt
        elif credit_amt > 0:
            tx_type = "CREDIT"
            amount_inr = credit_amt
        elif amount_col and amount_col in row:
            raw_amt = row[amount_col]
            amount_inr = parse_currency_amount(raw_amt)
            tx_type = "DEBIT"
        else:
            amount_inr = 0.0
            tx_type = "DEBIT"

        amount_paise = int(round(amount_inr * 100))

        # Check duplicate
        is_duplicate = False
        if parsed_d and amount_paise > 0:
            fp = compute_fingerprint(user_id, parsed_d, amount_paise, tx_type, narration)
            is_duplicate = fp in existing_fingerprints

        preview_rows.append({
            "row_index": idx + 1,
            "row_number": idx + 1,
            "raw_data": {str(k): ("" if pd.isna(v) else str(v)) for k, v in row.items()},
            "parsed_date": parsed_d.isoformat() if parsed_d else None,
            "narration": narration,
            "amount_inr": amount_inr,
            "transaction_type": tx_type,
            "is_duplicate": is_duplicate,
            "valid": parsed_d is not None and amount_inr > 0,
        })

    potential_duplicates_count = sum(1 for r in preview_rows if r.get("is_duplicate"))

    return {
        "filename": filename,
        "encoding": encoding,
        "total_columns": len(columns),
        "columns": columns,
        "headers": columns,
        "suggested_mapping": suggested_mapping,
        "preview_rows": preview_rows,
        "parsed_preview_rows": preview_rows,
        "total_detected_rows": len(df),
        "potential_duplicates": potential_duplicates_count,
    }

def execute_csv_import(
    file_bytes: bytes,
    filename: str,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    column_mapping: Dict[str, str],
    db: Session,
    bank_format: str = "GENERIC",
) -> Dict[str, Any]:
    """
    Ingest, validate, enrich, deduplicate, and batch insert statement transactions
    within an ACID database transaction. Generates row-level error audit logs.
    """
    # 1. Verify account belongs to user
    account = db.query(FinancialAccount).filter(
        FinancialAccount.id == account_id,
        FinancialAccount.user_id == user_id,
    ).first()
    if not account:
        raise ValueError("Invalid account or account does not belong to user.")

    # 2. Create ImportJob tracker
    import_job = ImportJob(
        user_id=user_id,
        filename=filename,
        bank_format=bank_format,
        status="PROCESSING",
        total_rows=0,
        imported_rows=0,
        duplicate_rows=0,
    )
    db.add(import_job)
    db.commit()
    db.refresh(import_job)

    # Check file size limit
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        raise ValueError(f"File size exceeds maximum limit of {MAX_FILE_SIZE_BYTES // (1024*1024)} MB")

    encoding = detect_encoding(file_bytes)
    text = file_bytes.decode(encoding)

    # 3. Read entire CSV
    df = pd.read_csv(io.StringIO(text))
    total_rows = len(df)
    import_job.total_rows = total_rows

    if total_rows > 10000:
        import_job.status = "FAILED"
        import_job.error_log = json.dumps([{
            "row_number": 0,
            "error": "Statement exceeds maximum allowable limit of 10,000 rows.",
            "raw_content": "",
        }])
        db.commit()
        raise ValueError("Statement exceeds maximum allowable limit of 10,000 rows. Please split the file into smaller date ranges.")

    date_col = column_mapping.get("date_col")
    narration_col = column_mapping.get("narration_col")
    debit_col = column_mapping.get("debit_col")
    credit_col = column_mapping.get("credit_col")
    amount_col = column_mapping.get("amount_col")
    type_col = column_mapping.get("type_col")
    ref_col = column_mapping.get("ref_col")

    # Preload user categories map {slug: Category}
    categories = {c.slug: c for c in db.query(TransactionCategory).all()}
    misc_cat = categories.get("miscellaneous") or list(categories.values())[0]

    # Preload existing user fingerprints for fast set membership
    existing_fingerprints = set(
        f[0] for f in db.query(Transaction.fingerprint).filter(Transaction.user_id == user_id).all()
    )

    imported_count = 0
    duplicate_count = 0
    failed_rows: List[Dict[str, Any]] = []

    net_balance_adjustment_paise = 0

    try:
        for idx, row in df.iterrows():
            row_num = idx + 2  # 1-indexed header + 1

            # Extract and validate Date
            raw_date = row.get(date_col) if date_col else None
            parsed_d = parse_indian_date(raw_date)
            if not parsed_d:
                failed_rows.append({
                    "row": row_num,
                    "reason": f"Invalid date format: '{raw_date}'",
                    "raw": str(row.to_dict()),
                })
                continue

            # Extract narration
            narration = str(row.get(narration_col, "")).strip() if narration_col else "Statement Item"
            if not narration or narration == "nan":
                narration = "Unlabeled Transaction"

            # Extract amounts and transaction type
            debit_amt = parse_currency_amount(row.get(debit_col)) if debit_col else 0.0
            credit_amt = parse_currency_amount(row.get(credit_col)) if credit_col else 0.0

            if debit_amt > 0:
                tx_type = "DEBIT"
                amount_inr = debit_amt
            elif credit_amt > 0:
                tx_type = "CREDIT"
                amount_inr = credit_amt
            elif amount_col and amount_col in row:
                amount_inr = parse_currency_amount(row[amount_col])
                raw_type = str(row.get(type_col, "")).upper() if type_col else ""
                if "CR" in raw_type or "CREDIT" in raw_type:
                    tx_type = "CREDIT"
                else:
                    tx_type = "DEBIT"
            else:
                failed_rows.append({
                    "row": row_num,
                    "reason": "Missing or zero debit/credit monetary amount",
                    "raw": str(row.to_dict()),
                })
                continue

            if amount_inr <= 0:
                failed_rows.append({
                    "row": row_num,
                    "reason": "Monetary amount must be strictly greater than 0",
                    "raw": str(row.to_dict()),
                })
                continue

            amount_paise = int(round(amount_inr * 100))

            # Deduplication Check via SHA-256 Fingerprint
            fp = compute_fingerprint(user_id, parsed_d, amount_paise, tx_type, narration)
            if fp in existing_fingerprints:
                duplicate_count += 1
                continue

            # Enrich with Categorization & Merchant normalization
            enrichment = categorize_transaction(
                narration=narration,
                tx_type=tx_type,
                amount_inr=amount_inr,
                db_session=db,
            )
            cat_slug = enrichment.get("category_slug", "miscellaneous")
            cat_obj = categories.get(cat_slug, misc_cat)
            merchant_name = enrichment.get("merchant_name") or normalize_merchant(narration)

            ref_id = str(row.get(ref_col, "")).strip() if ref_col and not pd.isna(row.get(ref_col)) else None

            # Create Transaction Record
            new_tx = Transaction(
                user_id=user_id,
                account_id=account_id,
                category_id=cat_obj.id,
                date=parsed_d,
                amount_paise=amount_paise,
                transaction_type=tx_type,
                narration=narration,
                raw_narration=str(row.to_dict()),
                merchant_name=merchant_name,
                payment_mode="NET_BANKING" if "ach" in narration.lower() or "neft" in narration.lower() else "UPI",
                reference_id=ref_id,
                fingerprint=fp,
                categorization_method=enrichment.get("method", "RULE"),
                categorization_confidence=enrichment.get("confidence", 0.90),
            )
            db.add(new_tx)

            # Keep track in memory to avoid intra-batch duplicates
            existing_fingerprints.add(fp)
            imported_count += 1

            if tx_type == "CREDIT":
                net_balance_adjustment_paise += amount_paise
            else:
                net_balance_adjustment_paise -= amount_paise

        # Adjust account current balance
        account.balance_paise += net_balance_adjustment_paise

        # Update ImportJob Record
        import_job.status = "COMPLETED"
        import_job.imported_rows = imported_count
        import_job.duplicate_rows = duplicate_count
        import_job.completed_at = datetime.now()
        if failed_rows:
            import_job.error_log = json.dumps(failed_rows)

        db.commit()
        db.refresh(import_job)

        failed_cnt = len(failed_rows)
        return {
            "job_id": str(import_job.id),
            "status": "COMPLETED",
            "total_rows": total_rows,
            "imported_rows": imported_count,
            "duplicate_rows": duplicate_count,
            "failed_rows": failed_rows,
            "failed_rows_count": failed_cnt,
            "failed_rows_list": failed_rows,
            "error_report_available": failed_cnt > 0,
            "message": f"Successfully imported {imported_count} new transactions into ledger ({duplicate_count} duplicates skipped).",
        }

    except Exception as e:
        db.rollback()
        import_job.status = "FAILED"
        import_job.error_log = str(e)
        import_job.completed_at = datetime.now()
        db.commit()
        raise RuntimeError(f"CSV import failed and was rolled back: {e}")

def sanitize_csv_cell(val: Any) -> str:
    """Defend against CSV/Formula injection in spreadsheet applications."""
    s = str(val) if val is not None else ""
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s

def generate_failed_rows_csv(failed_rows: List[Dict[str, Any]]) -> str:
    """Generate downloadable CSV string of row-level import errors with formula injection defense."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Row Number", "Failure Reason", "Raw Content"])
    for f in failed_rows:
        writer.writerow([
            f.get("row"),
            sanitize_csv_cell(f.get("reason")),
            sanitize_csv_cell(f.get("raw")),
        ])
    return output.getvalue()

