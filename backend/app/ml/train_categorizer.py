"""
Retraining script for FinPilot AI transaction categorization engine.
Evaluates on a held-out test split, persists versioned joblib artifacts,
and logs metrics to the ModelEvaluation database table.
"""
import sys
import os
import json
from datetime import datetime

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.ml.classifier import TransactionClassifier
from app.ml.dataset import SAMPLE_TRAINING_DATA
from app.db.session import SessionLocal
from app.models.model_evaluation import ModelEvaluation
from app.models.transaction import Transaction

def train_and_persist(version: str = "v1.0.0") -> dict:
    print(f"\n=======================================================")
    print(f"🚀 Training FinPilot AI Categorizer [{version}]")
    print(f"=======================================================")

    clf = TransactionClassifier(model_version=version)

    # Supplement training dataset with user-corrected transactions from database if available
    db = SessionLocal()
    training_data = list(SAMPLE_TRAINING_DATA)
    try:
        user_corrections = db.query(Transaction).filter(
            Transaction.categorization_method == "MANUAL",
            Transaction.raw_narration != None,
        ).all()
        for tx in user_corrections:
            if tx.category and tx.category.slug:
                training_data.append((tx.narration or tx.raw_narration, tx.category.slug, tx.merchant_name or ""))
        print(f"📊 Training corpus: {len(training_data)} total samples (including {len(user_corrections)} user corrections)")
    except Exception as e:
        print(f"⚠️ Could not load user corrections from DB ({e}). Using base dataset.")
    finally:
        db.close()

    metrics = clf.train_and_evaluate(data=training_data, test_size=0.20)

    print(f"✅ Training completed successfully!")
    print(f"   Accuracy:         {metrics['accuracy'] * 100:.2f}%")
    print(f"   Macro-F1 Score:   {metrics['macro_f1']:.4f}")
    print(f"   Macro-Precision:  {metrics['macro_precision']:.4f}")
    print(f"   Macro-Recall:     {metrics['macro_recall']:.4f}")
    print(f"   Classes Evaluated: {len(metrics['classes'])}")

    # Record evaluation record in the database
    db = SessionLocal()
    try:
        eval_record = ModelEvaluation(
            model_name="transaction_classifier",
            version=version,
            evaluation_type="STRATIFIED_TEST_SPLIT",
            metrics_json=json.dumps(metrics),
            sample_size=metrics["total_samples"],
            evaluated_at=datetime.now(),
        )
        db.add(eval_record)
        db.commit()
        print(f"💾 Logged evaluation record to 'model_evaluations' table (ID: {eval_record.id})")
    except Exception as e:
        print(f"⚠️ Failed to log to model_evaluations: {e}")
        db.rollback()
    finally:
        db.close()

    return metrics

if __name__ == "__main__":
    v = sys.argv[1] if len(sys.argv) > 1 else "v1.0.0"
    train_and_persist(v)
