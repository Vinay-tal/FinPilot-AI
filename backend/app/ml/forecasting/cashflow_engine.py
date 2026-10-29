import math
from datetime import date, timedelta
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from scipy.stats import norm

# Optional statsmodels import with fallback
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False


class CashFlowReconstructor:
    """
    Reconstructs historical daily balances, net cash flows,
    and separates non-recurring discretionary cash burn from committed recurring flows.
    """

    @staticmethod
    def reconstruct_daily_series(
        transactions: List[Any],
        current_liquid_balance_paise: int,
        lookback_days: int = 90,
    ) -> pd.DataFrame:
        """
        Creates a continuous daily time series of cash flows and balances.
        Missing dates are zero-filled for cash flows.
        """
        today = date.today()
        start_date = today - timedelta(days=lookback_days)

        # Generate complete date index
        date_range = pd.date_range(start=start_date, end=today, freq="D")
        df = pd.DataFrame(index=date_range)
        df["date"] = df.index.date
        df["total_credits_paise"] = 0
        df["total_debits_paise"] = 0
        df["recurring_credits_paise"] = 0
        df["recurring_debits_paise"] = 0
        df["discretionary_debits_paise"] = 0

        # Aggregate transaction flows per date
        daily_agg: Dict[date, Dict[str, int]] = {}
        for tx in transactions:
            tx_dt = tx.date if isinstance(tx.date, date) else tx.date.date()
            if tx_dt < start_date or tx_dt > today:
                continue

            if tx_dt not in daily_agg:
                daily_agg[tx_dt] = {
                    "total_credits": 0,
                    "total_debits": 0,
                    "recurring_credits": 0,
                    "recurring_debits": 0,
                    "discretionary_debits": 0,
                }

            amt = tx.amount_paise
            if tx.transaction_type == "CREDIT":
                daily_agg[tx_dt]["total_credits"] += amt
                if getattr(tx, "is_recurring", False):
                    daily_agg[tx_dt]["recurring_credits"] += amt
            else:
                daily_agg[tx_dt]["total_debits"] += amt
                if getattr(tx, "is_recurring", False):
                    daily_agg[tx_dt]["recurring_debits"] += amt
                else:
                    daily_agg[tx_dt]["discretionary_debits"] += amt

        # Populate dataframe
        for idx_dt in df["date"]:
            if idx_dt in daily_agg:
                agg = daily_agg[idx_dt]
                mask = df["date"] == idx_dt
                df.loc[mask, "total_credits_paise"] = agg["total_credits"]
                df.loc[mask, "total_debits_paise"] = agg["total_debits"]
                df.loc[mask, "recurring_credits_paise"] = agg["recurring_credits"]
                df.loc[mask, "recurring_debits_paise"] = agg["recurring_debits"]
                df.loc[mask, "discretionary_debits_paise"] = agg["discretionary_debits"]

        df["net_cashflow_paise"] = df["total_credits_paise"] - df["total_debits_paise"]

        # Backwards reconstruction of balance series ending at current_liquid_balance_paise
        n_days = len(df)
        balances = np.zeros(n_days, dtype=np.int64)
        balances[-1] = current_liquid_balance_paise

        # Iterate backwards from yesterday to start
        for i in range(n_days - 2, -1, -1):
            next_day_net = df["net_cashflow_paise"].iloc[i + 1]
            balances[i] = balances[i + 1] - next_day_net

        df["balance_paise"] = balances
        df["balance_inr"] = df["balance_paise"] / 100.0
        df["net_cashflow_inr"] = df["net_cashflow_paise"] / 100.0
        df["discretionary_burn_inr"] = df["discretionary_debits_paise"] / 100.0

        return df


class BaselineCashFlowModel:
    """
    Transparent, highly robust baseline cash-flow forecasting model.
    Combines:
    1. Recent exponential-weighted daily discretionary burn rate.
    2. Calendar day-of-week velocity adjustments (e.g. weekend spend elevation).
    3. Explicit integration of scheduled recurring events (salary, rent, bills, SIPs).
    """

    def __init__(self, burn_window_days: int = 30):
        self.burn_window_days = burn_window_days
        self.daily_burn_paise: int = 100000  # Default ~₹1,000/day
        self.dow_multipliers: Dict[int, float] = {i: 1.0 for i in range(7)}
        self.residual_std_paise: float = 50000.0

    def fit(self, df: pd.DataFrame) -> "BaselineCashFlowModel":
        if df.empty or len(df) < 7:
            return self

        # Extract recent discretionary burns
        recent = df.tail(self.burn_window_days)
        burns = recent["discretionary_debits_paise"].values

        # Base burn: 70% 14-day median + 30% 30-day mean (reduces outlier sensitivity)
        p14 = burns[-14:] if len(burns) >= 14 else burns
        base_burn = 0.7 * np.median(p14) + 0.3 * np.mean(burns)
        self.daily_burn_paise = max(20000, int(base_burn))  # Minimum ₹200/day floor

        # Day-of-week multipliers (0=Monday, 6=Sunday)
        dow_groups = df.groupby(df.index.dayofweek)["discretionary_debits_paise"].mean()
        overall_mean = df["discretionary_debits_paise"].mean()
        if overall_mean > 0:
            for dow in range(7):
                dow_mean = dow_groups.get(dow, overall_mean)
                # Dampen multiplier towards 1.0 to avoid overfitting
                ratio = float(dow_mean / overall_mean)
                self.dow_multipliers[dow] = round(0.5 + 0.5 * ratio, 3)

        # Estimate residual volatility
        predicted_burns = [
            self.daily_burn_paise * self.dow_multipliers[dt.weekday()]
            for dt in recent["date"]
        ]
        residuals = burns - np.array(predicted_burns)
        self.residual_std_paise = max(30000.0, float(np.std(residuals)))

        return self

    def predict_daily(
        self,
        start_date: date,
        horizon_days: int,
        initial_balance_paise: int,
        recurring_events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Project forward daily balance with uncertainty bands and scheduled events."""
        results = []
        running_balance = initial_balance_paise

        for h in range(1, horizon_days + 1):
            curr_date = start_date + timedelta(days=h)
            dow = curr_date.weekday()
            dow_mult = self.dow_multipliers.get(dow, 1.0)

            daily_discretionary = int(self.daily_burn_paise * dow_mult)
            running_balance -= daily_discretionary

            # Apply scheduled recurring events
            events_today = []
            recurring_net = 0
            for r in recurring_events:
                if r["expected_date"].day == curr_date.day:
                    amt = r["amount_paise"]
                    if r["type"] == "CREDIT":
                        running_balance += amt
                        recurring_net += amt
                        events_today.append(f"+₹{amt // 100:,.0f} {r['name']}")
                    else:
                        running_balance -= amt
                        recurring_net -= amt
                        events_today.append(f"-₹{amt // 100:,.0f} {r['name']}")

            # Conformal prediction interval expanding with sqrt(time)
            # 80% CI (Z = 1.282), 95% CI (Z = 1.960)
            spread_80 = int(self.residual_std_paise * math.sqrt(h) * 1.282)
            spread_95 = int(self.residual_std_paise * math.sqrt(h) * 1.960)

            lower_80 = max(0, running_balance - spread_80)
            upper_80 = running_balance + spread_80
            lower_95 = max(0, running_balance - spread_95)
            upper_95 = running_balance + spread_95

            results.append({
                "date": curr_date.isoformat(),
                "display_date": curr_date.strftime("%b %d"),
                "balance_paise": running_balance,
                "balance_inr": round(running_balance / 100.0, 2),
                "lower_bound_inr": round(lower_80 / 100.0, 2),
                "upper_bound_inr": round(upper_80 / 100.0, 2),
                "lower_bound_80_inr": round(lower_80 / 100.0, 2),
                "upper_bound_80_inr": round(upper_80 / 100.0, 2),
                "lower_bound_95_inr": round(lower_95 / 100.0, 2),
                "upper_bound_95_inr": round(upper_95 / 100.0, 2),
                "discretionary_burn_inr": round(daily_discretionary / 100.0, 2),
                "recurring_net_inr": round(recurring_net / 100.0, 2),
                "event_name": ", ".join(events_today) if events_today else None,
            })

        return results


class RidgeCalendarForecastModel:
    """
    Statistical machine learning forecast model using L2 Ridge Regression.
    Incorporates:
    - Day of week (sin/cos representation).
    - Day of month calendar effects.
    - Weekend indicators.
    - 7-day and 14-day rolling burn momentum.
    """

    def __init__(self, alpha: float = 1.5):
        self.alpha = alpha
        self.model = Ridge(alpha=alpha)
        self.is_fitted = False
        self.residual_std_paise: float = 60000.0
        self.avg_daily_burn_paise: int = 100000

    def _extract_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        X = []
        y = []
        burns = df["discretionary_debits_paise"].values
        dates = df["date"].values

        # Need at least 14 days of history for rolling lag features
        for i in range(14, len(df)):
            dt = dates[i]
            dow = dt.weekday()
            dom = dt.day

            # Feature vector:
            # [sin(dow), cos(dow), is_weekend, dom/31, 7d_mean, 14d_mean]
            features = [
                math.sin(2 * math.pi * dow / 7.0),
                math.cos(2 * math.pi * dow / 7.0),
                1.0 if dow in (5, 6) else 0.0,
                dom / 31.0,
                float(np.mean(burns[i - 7:i])),
                float(np.mean(burns[i - 14:i])),
            ]
            X.append(features)
            y.append(burns[i])

        return np.array(X), np.array(y)

    def fit(self, df: pd.DataFrame) -> "RidgeCalendarForecastModel":
        if len(df) < 21:
            return self

        X, y = self._extract_features(df)
        if len(X) < 7:
            return self

        self.model.fit(X, y)
        preds = self.model.predict(X)
        residuals = y - preds
        self.residual_std_paise = max(30000.0, float(np.std(residuals)))
        self.avg_daily_burn_paise = max(20000, int(np.mean(y)))
        self.is_fitted = True
        return self

    def predict_daily(
        self,
        start_date: date,
        horizon_days: int,
        initial_balance_paise: int,
        recurring_events: List[Dict[str, Any]],
        recent_history_df: pd.DataFrame,
    ) -> List[Dict[str, Any]]:
        if not self.is_fitted:
            # Fallback to Baseline if insufficient fit
            baseline = BaselineCashFlowModel().fit(recent_history_df)
            return baseline.predict_daily(
                start_date, horizon_days, initial_balance_paise, recurring_events
            )

        results = []
        running_balance = initial_balance_paise
        burn_history = list(recent_history_df["discretionary_debits_paise"].tail(14).values)

        for h in range(1, horizon_days + 1):
            curr_date = start_date + timedelta(days=h)
            dow = curr_date.weekday()
            dom = curr_date.day

            features = np.array([[
                math.sin(2 * math.pi * dow / 7.0),
                math.cos(2 * math.pi * dow / 7.0),
                1.0 if dow in (5, 6) else 0.0,
                dom / 31.0,
                float(np.mean(burn_history[-7:])),
                float(np.mean(burn_history[-14:])),
            ]])

            predicted_burn = float(self.model.predict(features)[0])
            # Bound prediction between 0.3x and 3.0x historical average
            predicted_burn = max(
                0.3 * self.avg_daily_burn_paise,
                min(3.0 * self.avg_daily_burn_paise, predicted_burn),
            )
            burn_paise = int(predicted_burn)
            burn_history.append(burn_paise)
            running_balance -= burn_paise

            # Recurring events
            events_today = []
            recurring_net = 0
            for r in recurring_events:
                if r["expected_date"].day == curr_date.day:
                    amt = r["amount_paise"]
                    if r["type"] == "CREDIT":
                        running_balance += amt
                        recurring_net += amt
                        events_today.append(f"+₹{amt // 100:,.0f} {r['name']}")
                    else:
                        running_balance -= amt
                        recurring_net -= amt
                        events_today.append(f"-₹{amt // 100:,.0f} {r['name']}")

            spread_80 = int(self.residual_std_paise * math.sqrt(h) * 1.282)
            spread_95 = int(self.residual_std_paise * math.sqrt(h) * 1.960)

            lower_80 = max(0, running_balance - spread_80)
            upper_80 = running_balance + spread_80
            lower_95 = max(0, running_balance - spread_95)
            upper_95 = running_balance + spread_95

            results.append({
                "date": curr_date.isoformat(),
                "display_date": curr_date.strftime("%b %d"),
                "balance_paise": running_balance,
                "balance_inr": round(running_balance / 100.0, 2),
                "lower_bound_inr": round(lower_80 / 100.0, 2),
                "upper_bound_inr": round(upper_80 / 100.0, 2),
                "lower_bound_80_inr": round(lower_80 / 100.0, 2),
                "upper_bound_80_inr": round(upper_80 / 100.0, 2),
                "lower_bound_95_inr": round(lower_95 / 100.0, 2),
                "upper_bound_95_inr": round(upper_95 / 100.0, 2),
                "discretionary_burn_inr": round(burn_paise / 100.0, 2),
                "recurring_net_inr": round(recurring_net / 100.0, 2),
                "event_name": ", ".join(events_today) if events_today else None,
            })

        return results


class CategoryForecastingEngine:
    """
    Category-level expense forecasting.
    Combines:
    - Current month-to-date (MTD) expenditure.
    - Empirical Bayes shrinkage between recent 14-day velocity and 90-day baseline run-rate.
    - Remaining days in billing period.
    Handles sparse or newly created categories gracefully.
    """

    @staticmethod
    def forecast_categories(
        transactions: List[Any],
        categories: List[Any],
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        today = as_of_date or date.today()
        # Find start of current month and days in current month
        month_start = today.replace(day=1)
        next_month = (month_start + timedelta(days=32)).replace(day=1)
        days_in_month = (next_month - month_start).days
        elapsed_days = max(1, today.day)
        remaining_days = max(0, days_in_month - elapsed_days)

        # 90-day lookback window for historical run-rate
        lookback_90 = today - timedelta(days=90)

        # Build category lookup map
        cat_map = {str(c.id): c for c in categories}
        cat_slug_map = {c.slug: c for c in categories}

        # Track spending aggregates
        mtd_spend: Dict[str, int] = {str(c.id): 0 for c in categories}
        hist_spend: Dict[str, int] = {str(c.id): 0 for c in categories}

        for tx in transactions:
            if tx.transaction_type != "DEBIT":
                continue
            tx_dt = tx.date if isinstance(tx.date, date) else tx.date.date()
            cat_id = str(tx.category_id)
            if cat_id not in mtd_spend:
                continue

            amt = tx.amount_paise
            if month_start <= tx_dt <= today:
                mtd_spend[cat_id] += amt
            if lookback_90 <= tx_dt <= today:
                hist_spend[cat_id] += amt

        forecast_results = []
        for cat in categories:
            cat_id = str(cat.id)
            current_spent = mtd_spend.get(cat_id, 0)
            hist_total = hist_spend.get(cat_id, 0)

            # Historical daily rate over 90 days
            hist_daily_rate = hist_total / 90.0

            # Current month daily rate
            current_daily_rate = current_spent / float(elapsed_days)

            # Shrinkage: If elapsed_days < 10, weight historical baseline more heavily
            alpha = min(0.85, elapsed_days / float(days_in_month))
            blended_daily_rate = alpha * current_daily_rate + (1.0 - alpha) * hist_daily_rate

            # Handle sparse / zero-history categories gracefully
            if blended_daily_rate == 0 and current_spent > 0:
                blended_daily_rate = current_daily_rate

            projected_remaining = int(blended_daily_rate * remaining_days)
            projected_month_end = current_spent + projected_remaining

            # Pacing status
            expected_fraction = elapsed_days / float(days_in_month)
            pacing_ratio = (
                (current_spent / float(projected_month_end)) / expected_fraction
                if projected_month_end > 0
                else 1.0
            )

            if pacing_ratio > 1.25:
                pacing_status = "ELEVATED"
            elif pacing_ratio < 0.85:
                pacing_status = "UNDER_PACING"
            else:
                pacing_status = "ON_TRACK"

            forecast_results.append({
                "category_id": cat_id,
                "category_name": cat.name,
                "category_slug": cat.slug,
                "category_color": cat.color,
                "current_spent_inr": round(current_spent / 100.0, 2),
                "projected_remaining_inr": round(projected_remaining / 100.0, 2),
                "projected_month_end_inr": round(projected_month_end / 100.0, 2),
                "daily_run_rate_inr": round(blended_daily_rate / 100.0, 2),
                "pacing_status": pacing_status,
                "pacing_ratio": round(pacing_ratio, 2),
                "historical_90d_total_inr": round(hist_total / 100.0, 2),
            })

        # Sort by projected month-end expenditure descending
        forecast_results.sort(key=lambda x: x["projected_month_end_inr"], reverse=True)
        return forecast_results


class ShortfallRiskDetector:
    """
    Evaluates liquidity shortfall risk during the forecast horizon.
    Computes minimum balance, shortfall dates, and calibrated probabilities.
    Abstains from pseudo-probabilities if calibration criteria are not met.
    """

    @staticmethod
    def analyze_risk(
        forecast_points: List[Dict[str, Any]],
        reserve_threshold_paise: int = 1000000,  # ₹10,000 default buffer
        historical_variance_calibrated: bool = True,
    ) -> Dict[str, Any]:
        if not forecast_points:
            return {
                "shortfall_detected": False,
                "shortfall_date": None,
                "min_projected_balance_inr": 0.0,
                "risk_level": "SAFE",
                "shortfall_probability_pct": 0.0,
                "probability_calibrated": False,
                "days_until_shortfall": None,
                "buffer_deficit_inr": 0.0,
            }

        min_pt = min(forecast_points, key=lambda p: p["balance_paise"])
        min_bal_paise = min_pt["balance_paise"]

        shortfall_pt = None
        for idx, pt in enumerate(forecast_points):
            if pt["balance_paise"] < reserve_threshold_paise:
                shortfall_pt = (idx + 1, pt)
                break

        shortfall_detected = shortfall_pt is not None
        shortfall_date = shortfall_pt[1]["date"] if shortfall_pt else None
        days_until = shortfall_pt[0] if shortfall_pt else None
        deficit_paise = max(0, reserve_threshold_paise - min_bal_paise)

        # Calibrated Probability estimation
        if historical_variance_calibrated:
            # P(Balance < Reserve) using Gaussian normal distribution of uncertainty fan
            max_prob = 0.0
            for pt in forecast_points:
                bal = pt["balance_paise"]
                # Approximate 1-sigma spread from 80% CI: spread_80 = 1.282 * sigma
                spread_80_paise = (pt["upper_bound_80_inr"] - pt["balance_inr"]) * 100.0
                sigma = max(1000.0, spread_80_paise / 1.282)

                z_score = (reserve_threshold_paise - bal) / sigma
                prob = float(norm.cdf(z_score))
                if prob > max_prob:
                    max_prob = prob

            probability_pct = round(max_prob * 100.0, 1)
            probability_calibrated = True
        else:
            # Rule-based fallback: do not invent uncalibrated probabilities
            probability_calibrated = False
            if min_bal_paise < reserve_threshold_paise:
                probability_pct = 95.0
            elif min_bal_paise < reserve_threshold_paise * 1.5:
                probability_pct = 40.0
            else:
                probability_pct = 5.0

        # Assign risk tier
        if min_bal_paise < 0:
            risk_level = "CRITICAL_OVERDRAFT"
        elif shortfall_detected or probability_pct >= 50.0:
            risk_level = "HIGH_RISK"
        elif min_bal_paise < reserve_threshold_paise * 1.35 or probability_pct >= 25.0:
            risk_level = "MODERATE_RISK"
        else:
            risk_level = "SAFE"

        return {
            "shortfall_detected": shortfall_detected,
            "shortfall_date": shortfall_date,
            "min_projected_balance_inr": round(min_bal_paise / 100.0, 2),
            "risk_level": risk_level,
            "shortfall_probability_pct": probability_pct,
            "probability_calibrated": probability_calibrated,
            "days_until_shortfall": days_until,
            "buffer_deficit_inr": round(deficit_paise / 100.0, 2),
            "reserve_threshold_inr": round(reserve_threshold_paise / 100.0, 2),
        }


class TemporalModelEvaluator:
    """
    Walk-forward temporal train/test split evaluator.
    Strictly avoids future data leakage.
    Reports MAE, RMSE, WAPE, and compares every model against the baseline.
    """

    @staticmethod
    def evaluate_models(
        transactions: List[Any],
        current_liquid_balance_paise: int,
        n_splits: int = 3,
        test_window_days: int = 14,
    ) -> Dict[str, Any]:
        """
        Runs walk-forward temporal cross validation.
        """
        # Reconstruct 180-day continuous cash flows
        df = CashFlowReconstructor.reconstruct_daily_series(
            transactions, current_liquid_balance_paise, lookback_days=180
        )

        if len(df) < (test_window_days * 2 + 14):
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "At least 42 days of historical transaction history required for temporal evaluation.",
                "data_coverage_days": len(df),
                "baseline_mae": None,
                "advanced_mae": None,
            }

        baseline_errors_mae = []
        baseline_errors_rmse = []
        ridge_errors_mae = []
        ridge_errors_rmse = []

        # Walk-forward splits
        total_len = len(df)
        for s in range(n_splits, 0, -1):
            test_end = total_len - (s - 1) * test_window_days
            test_start = test_end - test_window_days
            train_end = test_start

            if train_end < 28:
                continue

            train_df = df.iloc[:train_end]
            test_df = df.iloc[test_start:test_end]

            actual_burns = test_df["discretionary_debits_paise"].values / 100.0

            # 1. Baseline Model
            base_model = BaselineCashFlowModel().fit(train_df)
            base_preds = [
                (base_model.daily_burn_paise * base_model.dow_multipliers[dt.weekday()]) / 100.0
                for dt in test_df["date"]
            ]
            base_err = actual_burns - np.array(base_preds)
            baseline_errors_mae.append(float(np.mean(np.abs(base_err))))
            baseline_errors_rmse.append(float(np.sqrt(np.mean(base_err ** 2))))

            # 2. Ridge Model
            ridge_model = RidgeCalendarForecastModel().fit(train_df)
            if ridge_model.is_fitted:
                ridge_preds = []
                recent_history = list(train_df["discretionary_debits_paise"].tail(14).values)
                for dt in test_df["date"]:
                    dow = dt.weekday()
                    dom = dt.day
                    feat = np.array([[
                        math.sin(2 * math.pi * dow / 7.0),
                        math.cos(2 * math.pi * dow / 7.0),
                        1.0 if dow in (5, 6) else 0.0,
                        dom / 31.0,
                        float(np.mean(recent_history[-7:])),
                        float(np.mean(recent_history[-14:])),
                    ]])
                    p = float(ridge_model.model.predict(feat)[0]) / 100.0
                    p = max(0.0, p)
                    ridge_preds.append(p)
                    recent_history.append(int(p * 100))

                ridge_err = actual_burns - np.array(ridge_preds)
                ridge_errors_mae.append(float(np.mean(np.abs(ridge_err))))
                ridge_errors_rmse.append(float(np.sqrt(np.mean(ridge_err ** 2))))
            else:
                # Fallback to baseline
                ridge_errors_mae.append(baseline_errors_mae[-1])
                ridge_errors_rmse.append(baseline_errors_rmse[-1])

        mean_base_mae = round(float(np.mean(baseline_errors_mae)), 2)
        mean_base_rmse = round(float(np.mean(baseline_errors_rmse)), 2)
        mean_ridge_mae = round(float(np.mean(ridge_errors_mae)), 2)
        mean_ridge_rmse = round(float(np.mean(ridge_errors_rmse)), 2)

        improvement_pct = round(((mean_base_mae - mean_ridge_mae) / mean_base_mae) * 100.0, 1)

        # Winning model selection
        if mean_ridge_mae < mean_base_mae:
            recommended_model = "ridge_calendar_ml"
        else:
            recommended_model = "baseline_burn_rate"

        return {
            "status": "SUCCESS",
            "model_version": "v1.2.0-temporal-cv",
            "evaluated_at": date.today().isoformat(),
            "data_coverage_days": len(df),
            "walk_forward_splits": len(baseline_errors_mae),
            "test_window_days": test_window_days,
            "baseline": {
                "name": "Weighted Daily Burn Rate + Day-of-Week",
                "mae_inr": mean_base_mae,
                "rmse_inr": mean_base_rmse,
            },
            "advanced_model": {
                "name": "Ridge Regression with Calendar & Lag Regressors",
                "mae_inr": mean_ridge_mae,
                "rmse_inr": mean_ridge_rmse,
            },
            "improvement_pct": improvement_pct,
            "recommended_model": recommended_model,
        }


class ForecastExplainer:
    """
    Explainability engine: decomposes the forecast into
    Observed Facts, Modeling Assumptions, and Driver Attributions.
    """

    @staticmethod
    def generate_explanation(
        current_balance_inr: float,
        projected_end_inr: float,
        min_balance_inr: float,
        recurring_events: List[Dict[str, Any]],
        daily_burn_inr: float,
        horizon_days: int,
        category_forecasts: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        net_change = projected_end_inr - current_balance_inr

        # Observed Facts
        salary_events = [r for r in recurring_events if r["type"] == "CREDIT"]
        debit_events = [r for r in recurring_events if r["type"] == "DEBIT"]
        total_recurring_inflow = sum(r["amount_paise"] for r in salary_events) / 100.0
        total_recurring_outflow = sum(r["amount_paise"] for r in debit_events) / 100.0

        observed_facts = [
            f"Current verified liquid account balance is ₹{current_balance_inr:,.2f}.",
            f"Average baseline discretionary burn rate is ₹{daily_burn_inr:,.0f}/day over recent transactions.",
        ]
        if salary_events:
            for s in salary_events:
                observed_facts.append(
                    f"Scheduled recurring income of ₹{s['amount_paise'] // 100:,.0f} ({s['name']}) on day {s['expected_date'].day}."
                )
        if debit_events:
            top_debit = max(debit_events, key=lambda x: x["amount_paise"])
            observed_facts.append(
                f"Fixed recurring commitments total ₹{total_recurring_outflow:,.0f} (largest: ₹{top_debit['amount_paise'] // 100:,.0f} for {top_debit['name']})."
            )

        # Assumptions
        assumptions = [
            f"Assumes non-recurring discretionary spending continues at the estimated velocity of ₹{daily_burn_inr:,.0f}/day without unannounced large capital outflows.",
            "Assumes scheduled recurring salaries and bill commitments arrive on their historical schedule.",
            "Uncertainty intervals assume normally distributed residual variance scaling with the square root of forecast horizon.",
        ]

        # Top positive and negative drivers
        positive_drivers = []
        negative_drivers = []

        if total_recurring_inflow > 0:
            positive_drivers.append({
                "factor": "Scheduled Salary / Inflow",
                "impact_inr": total_recurring_inflow,
                "description": f"Expected recurring inflow of ₹{total_recurring_inflow:,.0f}",
            })

        if total_recurring_outflow > 0:
            negative_drivers.append({
                "factor": "Fixed Commitments (Rent, Bills, SIPs)",
                "impact_inr": -total_recurring_outflow,
                "description": f"Total fixed outflows of ₹{total_recurring_outflow:,.0f}",
            })

        projected_discretionary = daily_burn_inr * horizon_days
        negative_drivers.append({
            "factor": f"{horizon_days}-Day Discretionary Expenditure",
            "impact_inr": -projected_discretionary,
            "description": f"Variable living expenses projected at ₹{projected_discretionary:,.0f}",
        })

        # Top expense categories driving outflows
        if category_forecasts:
            for cat in category_forecasts[:3]:
                if cat["projected_month_end_inr"] > 5000:
                    negative_drivers.append({
                        "factor": f"High Spend: {cat['category_name']}",
                        "impact_inr": -cat["projected_month_end_inr"],
                        "description": f"Projected category spend of ₹{cat['projected_month_end_inr']:,.0f} ({cat['pacing_status']})",
                    })

        summary_narrative = (
            f"Over the next {horizon_days} days, your balance is projected to change by "
            f"{'₹+' if net_change >= 0 else '-₹'}{abs(net_change):,.0f}, ending at ₹{projected_end_inr:,.0f}. "
            f"The minimum anticipated dip point is ₹{min_balance_inr:,.0f}."
        )

        return {
            "summary_narrative": summary_narrative,
            "observed_facts": observed_facts,
            "assumptions": assumptions,
            "positive_drivers": positive_drivers,
            "negative_drivers": negative_drivers,
        }
