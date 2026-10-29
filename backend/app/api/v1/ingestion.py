import uuid
import json
from datetime import date
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.account import FinancialAccount
from app.models.import_job import ImportJob
from app.models.category import TransactionCategory
from app.services.csv_import_service import (
    preview_csv_statement,
    execute_csv_import,
    generate_failed_rows_csv,
)
from app.services.sms_parser_service import get_sms_parser, SMSParseResult
from app.services.categorization_service import categorize_transaction
from app.services.transaction_service import create_transaction
from app.schemas.transaction import TransactionCreate

router = APIRouter(prefix="/ingestion", tags=["Transaction Ingestion"])

import os
ALLOWED_CSV_MIME_TYPES = {"text/csv", "application/vnd.ms-excel", "text/plain", "application/csv", "application/octet-stream"}
MAX_CSV_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/csv-preview")
async def preview_csv(
    account_id: uuid.UUID = Form(...),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Upload statement file and preview column mappings and rows before importing."""
    # 1. Filename & extension check
    safe_filename = os.path.basename(file.filename or "statement.csv")
    if not safe_filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are currently supported.",
        )

    # 2. Content-type check if provided
    if file.content_type and file.content_type.lower() not in ALLOWED_CSV_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'. Expected CSV format.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_CSV_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowable limit of 10 MB.",
        )

    try:
        preview = preview_csv_statement(
            file_bytes=file_bytes,
            filename=safe_filename,
            db=db,
            user_id=current_user.id,
            account_id=account_id,
        )
        return preview
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to parse statement preview.")

@router.post("/csv-import")
async def import_csv(
    account_id: uuid.UUID = Form(...),
    column_mapping: str = Form(...),
    bank_format: str = Form(default="GENERIC"),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Execute ACID batch import of CSV statement with deduplication and error auditing."""
    safe_filename = os.path.basename(file.filename or "statement.csv")
    if not safe_filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV files (.csv) are supported.",
        )

    if file.content_type and file.content_type.lower() not in ALLOWED_CSV_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MIME type '{file.content_type}'. Expected CSV format.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_CSV_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds maximum allowable limit of 10 MB.",
        )

    try:
        mapping_dict = json.loads(column_mapping)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format for column_mapping.",
        )

    try:
        result = execute_csv_import(
            file_bytes=file_bytes,
            filename=safe_filename,
            account_id=account_id,
            user_id=current_user.id,
            column_mapping=mapping_dict,
            db=db,
            bank_format=bank_format,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV statement import failed.")

@router.get("/jobs")
def list_import_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve audit history of CSV statement imports."""
    jobs = db.query(ImportJob).filter(
        ImportJob.user_id == current_user.id
    ).order_by(ImportJob.created_at.desc()).limit(20).all()

    return [
        {
            "id": str(j.id),
            "filename": j.filename,
            "bank_format": j.bank_format,
            "status": j.status,
            "total_rows": j.total_rows,
            "imported_rows": j.imported_rows,
            "duplicate_rows": j.duplicate_rows,
            "created_at": j.created_at.isoformat(),
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
            "has_errors": bool(j.error_log),
        }
        for j in jobs
    ]

@router.get("/jobs/{job_id}/errors.csv")
def download_job_errors_csv(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Download row-level validation errors from an import job as a CSV report."""
    job = db.query(ImportJob).filter(
        ImportJob.id == job_id,
        ImportJob.user_id == current_user.id,
    ).first()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Import job not found.")

    if not job.error_log:
        return Response(content="Row Number,Failure Reason,Raw Content\n", media_type="text/csv")

    try:
        failed_rows = json.loads(job.error_log)
        csv_text = generate_failed_rows_csv(failed_rows)
    except Exception:
        csv_text = f"Row Number,Failure Reason,Raw Content\n1,Fatal Job Error,\"{job.error_log}\"\n"

    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=import_errors_{job_id}.csv"},
    )

class SMSParseRequest(BaseModel if "BaseModel" in locals() else object):
    pass

from pydantic import BaseModel

class SMSParseInput(BaseModel):
    sms_text: str

@router.post("/parse-sms")
def parse_sms_message(
    body: SMSParseInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Parse SMS string, extract transaction fields, and suggest category & merchant."""
    parser = get_sms_parser()
    result = parser.parse(body.sms_text)

    if not result.success:
        return result.model_dump()

    # Enrich with categorization
    enrichment = categorize_transaction(
        narration=result.clean_narration or result.raw_narration,
        tx_type=result.transaction_type,
        amount_inr=result.amount_inr,
        db_session=db,
    )
    result_dict = result.model_dump()
    result_dict["suggested_category_slug"] = enrichment.get("category_slug", "miscellaneous")
    result_dict["categorization_method"] = enrichment.get("method", "RULE")
    result_dict["categorization_confidence"] = enrichment.get("confidence", 0.95)

    # Resolve category details
    cat = db.query(TransactionCategory).filter(TransactionCategory.slug == result_dict["suggested_category_slug"]).first()
    if cat:
        result_dict["category_id"] = str(cat.id)
        result_dict["category_name"] = cat.name
        result_dict["category_color"] = cat.color

    return result_dict

class SMSImportInput(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID
    amount_inr: float
    transaction_type: str
    date: str
    narration: str
    merchant_name: Optional[str] = None
    payment_mode: str = "UPI"
    reference_id: Optional[str] = None

@router.post("/import-sms-transaction")
def import_sms_transaction_to_ledger(
    body: SMSImportInput,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """1-click commit of parsed SMS transaction into live ledger."""
    amount_paise = int(round(body.amount_inr * 100))
    tx_create = TransactionCreate(
        account_id=body.account_id,
        category_id=body.category_id,
        date=date.fromisoformat(body.date),
        amount_paise=amount_paise,
        transaction_type=body.transaction_type,
        narration=body.narration,
        merchant_name=body.merchant_name,
        payment_mode=body.payment_mode,
        reference_id=body.reference_id,
    )
    created_tx = create_transaction(
        db=db,
        user_id=current_user.id,
        tx_in=tx_create,
        categorization_method="RULE",
        categorization_confidence=0.98,
        allow_duplicate=False,
    )
    return {
        "status": "success",
        "transaction_id": str(created_tx.id),
        "message": "Transaction successfully imported into ledger from SMS.",
    }
