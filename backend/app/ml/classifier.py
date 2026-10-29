import os
import re
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, accuracy_score, confusion_matrix

from app.ml.dataset import SAMPLE_TRAINING_DATA

logger = logging.getLogger(__name__)

ARTIFACTS_DIR = os.path.join(os.path.dirname(__file__), "artifacts")
MODEL_PATH = os.path.join(ARTIFACTS_DIR, "classifier_v1.joblib")
METADATA_PATH = os.path.join(ARTIFACTS_DIR, "metadata.json")

def clean_text_for_ml(text: str) -> str:
    """Preprocess narration text: lowercase, remove ref IDs/dates/noise, normalize whitespace."""
    if not text:
        return ""
    t = text.lower()
    # Remove UPI prefix noise
    t = re.sub(r"upi/[\w.-]+@[\w.-]+/?", " ", t)
    # Remove alphanumeric reference hashes/UUIDs (e.g., 629104829102, 0d24926cb...)
    t = re.sub(r"\b[a-f0-9]{10,}\b", " ", t)
    t = re.sub(r"\b\d{6,}\b", " ", t)
    # Remove special punctuation
    t = re.sub(r"[^a-zA-Z\s]", " ", t)
    # Normalize whitespace
    return " ".join(t.split())

class TransactionClassifier:
    """Production ML text classification pipeline for financial transaction categorization."""

    def __init__(self, model_version: str = "v1.0.0"):
        self.version = model_version
        self.pipeline: Optional[Pipeline] = None
        self.classes_: List[str] = []
        self.metadata: Dict[str, Any] = {}

    def build_pipeline(self) -> Pipeline:
        return Pipeline([
            ("tfidf", TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                sublinear_tf=True,
                strip_accents="unicode",
            )),
            ("clf", LogisticRegression(
                C=2.5,
                max_iter=1000,
                random_state=42,
                class_weight="balanced",
            )),
        ])

    def train_and_evaluate(
        self,
        data: Optional[List[Tuple[str, str, str]]] = None,
        test_size: float = 0.20,
    ) -> Dict[str, Any]:
        """
        Trains model on labeled data using a stratified held-out test split
        to evaluate generalization performance without data leakage.
        """
        raw_data = data or SAMPLE_TRAINING_DATA
        texts = [clean_text_for_ml(item[0]) for item in raw_data]
        labels = [item[1] for item in raw_data]

        # Stratified train/test split to avoid data leakage
        X_train, X_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=42, stratify=labels
        )

        pipeline = self.build_pipeline()
        pipeline.fit(X_train, y_train)

        # Predictions on held-out test set
        y_pred = pipeline.predict(X_test)
        classes = sorted(list(set(labels)))

        acc = float(accuracy_score(y_test, y_pred))
        macro_f1 = float(f1_score(y_test, y_pred, average="macro", zero_division=0))
        macro_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        macro_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))

        clf_report = classification_report(y_test, y_pred, output_dict=True, zero_division=0)
        conf_mat = confusion_matrix(y_test, y_pred, labels=classes).tolist()

        self.pipeline = pipeline
        self.classes_ = classes
        self.metadata = {
            "version": self.version,
            "trained_at": datetime.now().isoformat(),
            "total_samples": len(raw_data),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "accuracy": round(acc, 4),
            "macro_f1": round(macro_f1, 4),
            "macro_precision": round(macro_prec, 4),
            "macro_recall": round(macro_rec, 4),
            "classes": classes,
            "per_class_f1": {k: round(v["f1-score"], 3) for k, v in clf_report.items() if isinstance(v, dict)},
            "confusion_matrix": conf_mat,
        }

        self.save()
        logger.info(f"Model {self.version} trained: Accuracy={acc:.4f}, Macro-F1={macro_f1:.4f}")
        return self.metadata

    def predict(self, narration: str) -> Tuple[str, float]:
        """Predict category slug and confidence probability."""
        if not self.pipeline:
            raise RuntimeError("Classifier model is not trained or loaded.")

        cleaned = clean_text_for_ml(narration)
        if not cleaned:
            return "miscellaneous", 0.0

        probs = self.pipeline.predict_proba([cleaned])[0]
        max_idx = int(np.argmax(probs))
        predicted_class = self.pipeline.classes_[max_idx]
        confidence = float(probs[max_idx])

        return predicted_class, round(confidence, 4)

    def save(self, filepath: str = MODEL_PATH, meta_path: str = METADATA_PATH) -> None:
        """Persist model pipeline and evaluation metadata."""
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump(self.pipeline, filepath)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadata, f, indent=2)

    def load(self, filepath: str = MODEL_PATH, meta_path: str = METADATA_PATH) -> bool:
        """Load persisted model artifact from disk."""
        if not os.path.exists(filepath):
            return False
        try:
            self.pipeline = joblib.load(filepath)
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    self.metadata = json.load(f)
                    self.version = self.metadata.get("version", "v1.0.0")
                    self.classes_ = self.metadata.get("classes", [])
            return True
        except Exception as e:
            logger.error(f"Failed to load ML model from {filepath}: {e}")
            return False

_classifier_instance: Optional[TransactionClassifier] = None

def get_transaction_classifier() -> TransactionClassifier:
    """Singleton getter for loaded transaction classifier with auto-initialization."""
    global _classifier_instance
    if _classifier_instance is None:
        clf = TransactionClassifier()
        loaded = clf.load()
        if not loaded:
            logger.info("No saved model artifact found. Training initial baseline model...")
            clf.train_and_evaluate()
        _classifier_instance = clf
    return _classifier_instance
