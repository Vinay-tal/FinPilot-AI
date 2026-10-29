import uuid
from datetime import datetime, date, timedelta
from typing import Dict, Any, List, Optional
from collections import defaultdict
import numpy as np
from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from app.models.category import TransactionCategory

def detect_recurring_patterns(
    db: Session,
    user_id: uuid.UUID,
    lookback_days: int = 180,
    amount_tolerance_pct: float = 5.0,
) -> List[Dict[str, Any]]:
    """
    Detect recurring payment patterns based on merchant, amount consistency,
    and cadence intervals (weekly, monthly, yearly).
    """
    start_date = date.today() - timedelta(days=lookback_days)
    txs = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.transaction_type == "DEBIT",
    ).order_by(Transaction.date.asc()).all()

    # Group transactions by merchant (or cleaned narration)
    grouped: Dict[str, List[Transaction]] = defaultdict(list)
    for tx in txs:
        key = tx.merchant_name or tx.narration.split()[0]
        if key and len(key) >= 3:
            grouped[key.strip().lower()].append(tx)

    recurring_candidates: List[Dict[str, Any]] = []

    for key, items in grouped.items():
        if len(items) < 2:
            continue

        amounts_inr = [t.amount_paise / 100.0 for t in items]
        mean_amt = float(np.mean(amounts_inr))
        std_amt = float(np.std(amounts_inr))

        # Check amount consistency (within tolerance)
        cv = (std_amt / mean_amt * 100) if mean_amt > 0 else 0
        if cv > amount_tolerance_pct and std_amt > 50:
            continue

        # Check interval timing
        dates = [t.date for t in items]
        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        if not intervals:
            continue

        mean_interval = float(np.mean(intervals))

        frequency = None
        if 25 <= mean_interval <= 35:
            frequency = "MONTHLY"
        elif 6 <= mean_interval <= 8:
            frequency = "WEEKLY"
        elif 13 <= mean_interval <= 16:
            frequency = "BIWEEKLY"
        elif 85 <= mean_interval <= 95:
            frequency = "QUARTERLY"
        elif 350 <= mean_interval <= 380:
            frequency = "YEARLY"

        if frequency:
            last_date = dates[-1]
            next_date = last_date + timedelta(days=round(mean_interval))
            first_tx = items[0]

            recurring_candidates.append({
                "merchant_name": first_tx.merchant_name or key.title(),
                "category_id": str(first_tx.category_id),
                "category_name": first_tx.category.name if first_tx.category else "Uncategorized",
                "frequency": frequency,
                "expected_amount_inr": round(mean_amt, 2),
                "expected_amount_paise": int(round(mean_amt * 100)),
                "occurrences": len(items),
                "last_seen_date": last_date.isoformat(),
                "next_expected_date": next_date.isoformat(),
                "confidence": round(max(0.70, 1.0 - (cv / 100.0)), 2),
            })

    return recurring_candidates

def detect_near_duplicate_warnings(
    db: Session,
    user_id: uuid.UUID,
    days_window: int = 1,
) -> List[Dict[str, Any]]:
    """
    Detect near-duplicate transactions (same amount & merchant within 24-48 hours),
    often caused by duplicate gateway retries or double swipes.
    """
    txs = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
    ).order_by(Transaction.date.desc()).limit(150).all()

    warnings: List[Dict[str, Any]] = []
    seen = set()

    for i in range(len(txs)):
        for j in range(i + 1, len(txs)):
            t1, t2 = txs[i], txs[j]
            if abs((t1.date - t2.date).days) <= days_window and t1.amount_paise == t2.amount_paise:
                m1 = (t1.merchant_name or t1.narration[:15]).lower()
                m2 = (t2.merchant_name or t2.narration[:15]).lower()
                if m1 == m2 and (t1.id, t2.id) not in seen:
                    seen.add((t1.id, t2.id))
                    seen.add((t2.id, t1.id))
                    warnings.append({
                        "primary_tx_id": str(t1.id),
                        "duplicate_tx_id": str(t2.id),
                        "merchant": t1.merchant_name or t1.narration,
                        "amount_inr": t1.amount_paise / 100.0,
                        "date_1": t1.date.isoformat(),
                        "date_2": t2.date.isoformat(),
                        "warning": "Potential double payment detected for same amount and merchant.",
                    })

    return warnings

def detect_unusual_spending_anomalies(
    db: Session,
    user_id: uuid.UUID,
    lookback_days: int = 90,
    iqr_multiplier: float = 1.75,
) -> List[Dict[str, Any]]:
    """
    Detect statistical spending anomalies per category using robust IQR (Interquartile Range)
    and Median Absolute Deviation (MAD) methods.
    """
    start_date = date.today() - timedelta(days=lookback_days)
    txs = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date,
        Transaction.transaction_type == "DEBIT",
    ).all()

    by_category: Dict[str, List[Transaction]] = defaultdict(list)
    for t in txs:
        by_category[str(t.category_id)].append(t)

    anomalies: List[Dict[str, Any]] = []

    for cat_id, items in by_category.items():
        if len(items) < 5:
            continue

        amounts = np.array([t.amount_paise / 100.0 for t in items])
        q25, q50, q75 = np.percentile(amounts, [25, 50, 75])
        iqr = q75 - q25

        if iqr <= 0:
            continue

        upper_bound = q75 + (iqr_multiplier * iqr)

        for tx in items:
            amt = tx.amount_paise / 100.0
            if amt > upper_bound:
                fold_increase = round(amt / q50, 1) if q50 > 0 else 2.0
                cat_name = tx.category.name if tx.category else "Category"

                anomalies.append({
                    "transaction_id": str(tx.id),
                    "date": tx.date.isoformat(),
                    "narration": tx.narration,
                    "merchant_name": tx.merchant_name,
                    "amount_inr": amt,
                    "category_name": cat_name,
                    "median_inr": round(float(q50), 2),
                    "upper_threshold_inr": round(float(upper_bound), 2),
                    "fold_increase": fold_increase,
                    "severity": "CRITICAL" if fold_increase >= 3.0 else "WARNING",
                    "explanation": f"Amount of ₹{amt:,.2f} is {fold_increase}x higher than your typical {cat_name} median of ₹{q50:,.2f}.",
                })

    return sorted(anomalies, key=lambda x: x["fold_increase"], reverse=True)

def get_merchant_spending_summaries(
    db: Session,
    user_id: uuid.UUID,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """Aggregate spending by normalized merchant with ticket sizes and category."""
    txs = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.transaction_type == "DEBIT",
    ).all()

    by_merchant: Dict[str, List[Transaction]] = defaultdict(list)
    for t in txs:
        m = t.merchant_name or "Other / Direct Transfer"
        by_merchant[m].append(t)

    summaries = []
    for merchant, items in by_merchant.items():
        total_paise = sum(i.amount_paise for i in items)
        amounts_inr = [i.amount_paise / 100.0 for i in items]
        first_date = min(i.date for i in items)
        last_date = max(i.date for i in items)
        cat_name = items[0].category.name if items[0].category else "General"

        summaries.append({
            "merchant_name": merchant,
            "category_name": cat_name,
            "total_spent_inr": round(total_paise / 100.0, 2),
            "total_spent_paise": total_paise,
            "transaction_count": len(items),
            "avg_ticket_size_inr": round(float(np.mean(amounts_inr)), 2),
            "max_ticket_size_inr": round(float(np.max(amounts_inr)), 2),
            "first_seen_date": first_date.isoformat(),
            "last_seen_date": last_date.isoformat(),
        })

    # Sort by total spent descending
    summaries.sort(key=lambda x: x["total_spent_paise"], reverse=True)
    return summaries[:limit]
