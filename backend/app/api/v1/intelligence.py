import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.model_evaluation import ModelEvaluation
from app.services.intelligence_service import (
    detect_recurring_patterns,
    detect_near_duplicate_warnings,
    detect_unusual_spending_anomalies,
    get_merchant_spending_summaries,
)
from app.ml.train_categorizer import train_and_persist
from app.ml.classifier import get_transaction_classifier, METADATA_PATH

router = APIRouter(prefix="/intelligence", tags=["Transaction Intelligence"])

@router.get("/recurring")
def get_recurring_commitments(
    lookback_days: int = Query(default=180, ge=30, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Detect recurring payments and subscriptions from historical ledger intervals."""
    return detect_recurring_patterns(db, current_user.id, lookback_days=lookback_days)

@router.get("/duplicates")
def get_duplicate_warnings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Detect near-duplicate debit transactions within 24-48 hours."""
    return detect_near_duplicate_warnings(db, current_user.id)

@router.get("/anomalies")
def get_spending_anomalies(
    lookback_days: int = Query(default=90, ge=30, le=365),
    iqr_multiplier: float = Query(default=1.75, ge=1.0, le=3.5),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Detect unusual spending anomalies using robust Interquartile Range (IQR) method."""
    return detect_unusual_spending_anomalies(db, current_user.id, lookback_days, iqr_multiplier)

@router.get("/merchants")
def get_merchant_summaries(
    limit: int = Query(default=15, ge=5, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieve normalized merchant spending aggregations and average ticket sizes."""
    return get_merchant_spending_summaries(db, current_user.id, limit=limit)

@router.get("/model-evaluation")
def get_model_evaluation_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieve active ML categorizer metadata, test set Macro-F1 score, and training history."""
    # Check DB latest evaluation
    latest_eval = db.query(ModelEvaluation).filter(
        ModelEvaluation.model_name == "transaction_classifier"
    ).order_by(ModelEvaluation.evaluated_at.desc()).first()

    if latest_eval:
        try:
            metrics = json.loads(latest_eval.metrics_json)
            metrics["evaluation_id"] = str(latest_eval.id)
            metrics["evaluated_at"] = latest_eval.evaluated_at.isoformat()
            return metrics
        except Exception:
            pass

    # Fallback to metadata.json file artifact
    if os.path.exists(METADATA_PATH):
        try:
            with open(METADATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass

    # If no model trained yet, return baseline status
    clf = get_transaction_classifier()
    return clf.metadata or {
        "version": "v1.0.0",
        "status": "NOT_TRAINED",
        "accuracy": 0.0,
        "macro_f1": 0.0,
        "classes": [],
    }

@router.post("/retrain-model")
def retrain_categorizer_model(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Trigger retraining of the ML categorizer with latest user data and evaluations."""
    new_version = f"v{datetime.now().strftime('%Y%m%d.%H%M')}"
    metrics = train_and_persist(version=new_version)
    return {
        "status": "success",
        "version": new_version,
        "metrics": metrics,
    }
