# FinPilot AI: RESTful API Specification

**Version:** 1.0.0  
**Base Path:** `/api/v1`  
**Protocol:** HTTPS / JSON  
**Auth Header:** `Authorization: Bearer <jwt_access_token>`  

---

## 1. Global Standards & Error Format

All error responses adhere to RFC 7807 structured format:
```json
{
  "status_code": 400,
  "error_code": "VALIDATION_FAILED",
  "message": "Invalid date format provided for transaction import.",
  "details": {
    "field": "date",
    "expected": "YYYY-MM-DD or DD/MM/YYYY"
  }
}
```

---

## 2. Authentication & User Profile (`/auth`)

### 2.1 `POST /auth/register`
Creates a new user profile.
- **Request Body:**
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "full_name": "Rahul Sharma",
    "currency": "INR"
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "full_name": "Rahul Sharma",
      "currency": "INR"
    },
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
  }
  ```

### 2.2 `POST /auth/login`
Authenticates user credentials and issues token.
- **Request Body:** (Form or JSON)
  ```json
  {
    "email": "user@example.com",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK):** JWT token and user profile object.

### 2.3 `POST /auth/demo-login`
Instant one-click authentication as seeded demo user **Rahul Sharma** for zero-friction evaluation.
- **Response (200 OK):** Demo user token and profile.

### 2.4 `GET /auth/me`
Retrieves authenticated user profile.
- **Response (200 OK):** User details, account counts, demo flag.

---

## 3. Financial Dashboard (`/dashboard`)

### 3.1 `GET /dashboard/summary`
Core financial telemetry aggregated over a time period.
- **Query Params:** `period` (`current_month`, `last_30_days`, `last_90_days`, `ytd`)
- **Response (200 OK):**
  ```json
  {
    "period": "current_month",
    "total_income": 125000.00,
    "total_expenses": 72450.00,
    "net_savings": 52550.00,
    "savings_rate": 42.04,
    "total_liquid_balance": 184500.00,
    "total_debt_balance": 14200.00,
    "health_score": 82,
    "health_grade": "Excellent",
    "active_anomalies_count": 2,
    "budget_status": {
      "total_budgeted": 75000.00,
      "total_spent": 72450.00,
      "percent_consumed": 96.6
    }
  }
  ```

### 3.2 `GET /dashboard/cashflow-trend`
Historical time-series trend of monthly income vs expenses.
- **Query Params:** `months` (default `6`, max `24`)
- **Response (200 OK):** Array of monthly snapshots `[{ "month": "2024-05", "income": 125000, "expenses": 68000, "net": 57000 }]`.

### 3.3 `GET /dashboard/category-breakdown`
Spending distribution grouped by top categories with percentage shares.

---

## 4. Transactions Ledger (`/transactions`)

### 4.1 `GET /transactions`
Paginated, filterable, searchable transaction ledger.
- **Query Params:**
  - `page` (int, default 1)
  - `limit` (int, default 20)
  - `search` (string)
  - `category_id` (int)
  - `account_id` (int)
  - `start_date` (YYYY-MM-DD)
  - `end_date` (YYYY-MM-DD)
  - `type` (`DEBIT` or `CREDIT`)
- **Response (200 OK):** Paginated transactions with metadata.

### 4.2 `POST /transactions`
Creates a single transaction with automatic rule & ML categorization.
- **Request Body:**
  ```json
  {
    "account_id": 1,
    "date": "2024-10-18",
    "amount": 450.00,
    "transaction_type": "DEBIT",
    "narration": "UPI/428192837/SWIGGY/BANGALORE",
    "payment_mode": "UPI"
  }
  ```
- **Response (201 Created):** Assigned category, categorization method (`RULE` / `ML`), confidence score, anomaly check status.

### 4.3 `PUT /transactions/{id}`
Updates transaction details (e.g. category modification). Triggers auto-override recording to refine ML model.

### 4.4 `DELETE /transactions/{id}`
Soft or hard deletes a transaction record.

---

## 5. CSV Bank Statement Import & Export (`/import` & `/export`)

### 5.1 `POST /import/parse-csv`
Uploads raw bank statement CSV, detects columns, and validates structure.
- **Form Data:** `file` (multipart/form-data), `bank_format` (`auto`, `hdfc`, `sbi`, `icici`, `axis`, `generic`)
- **Response (200 OK):**
  ```json
  {
    "detected_headers": ["Date", "Narration", "Chq/Ref No", "Withdrawal (Dr)", "Deposit (Cr)", "Balance"],
    "suggested_mapping": {
      "date": "Date",
      "narration": "Narration",
      "debit": "Withdrawal (Dr)",
      "credit": "Deposit (Cr)",
      "balance": "Balance",
      "reference_id": "Chq/Ref No"
    },
    "total_rows": 128,
    "preview_rows": [
      {
        "row_index": 1,
        "date": "2024-10-14",
        "narration": "UPI-SWIGGY-BANGALORE-42819283",
        "amount": 540.00,
        "type": "DEBIT",
        "predicted_category": "Food & Dining",
        "confidence": 0.98,
        "is_duplicate": false
      }
    ]
  }
  ```

### 5.2 `POST /import/commit`
Commits previewed, user-verified transactions into ledger with deduplication.
- **Response (200 OK):** Count of inserted, skipped duplicates, and categorization summary.

### 5.3 `GET /export/transactions-csv`
Exports filtered transaction records to standard CSV file.

### 5.4 `GET /export/financial-report-pdf`
Generates clean, executive PDF summary report with charts and health metrics.

---

## 6. Indian Bank SMS Parser (`/sms`)

### 6.1 `POST /sms/parse`
Parses raw transactional SMS string into structured data.
- **Request Body:**
  ```json
  {
    "sms_text": "Sent Rs.550.00 from HDFC Bank A/C *4821 to Swiggy on 14-OCT-24. UPI: 428719283741."
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "success": true,
    "bank": "HDFC Bank",
    "amount": 550.00,
    "currency": "INR",
    "transaction_type": "DEBIT",
    "account_mask": "*4821",
    "merchant": "Swiggy",
    "date": "2024-10-14",
    "reference_id": "428719283741",
    "predicted_category": "Food & Dining",
    "confidence": 0.99
  }
  ```

### 6.2 `POST /sms/commit`
Directly converts parsed SMS transaction into confirmed ledger record.

---

## 7. Budgets & Pacing (`/budgets`)

### 7.1 `GET /budgets`
Retrieves monthly category budgets with live actuals and pacing metrics.
- **Query Params:** `month`, `year`
- **Response (200 OK):** List of budget objects with `amount`, `spent`, `remaining`, `pacing_pct`, `alert_status`.

### 7.2 `POST /budgets` & `PUT /budgets/{id}`
Create or update monthly budget allocations.

---

## 8. Recurring Expenses & Subscriptions (`/recurring`)

### 8.1 `GET /recurring`
Lists all active and detected recurring obligations.

### 8.2 `POST /recurring/detect`
Executes periodicity algorithm on historical ledger to detect newly emerged recurring subscriptions, bills, and salary patterns.

---

## 9. Cash Flow Forecasting (`/forecasting`)

### 9.1 `GET /forecasting/cashflow`
Projects future account balance and cash flow for 30, 60, or 90 days.
- **Query Params:** `days` (default `30`), `account_id` (optional)
- **Response (200 OK):**
  ```json
  {
    "horizon_days": 30,
    "model_used": "Holt-Winters Seasonal Smoothing + Event Schedule",
    "shortfall_detected": false,
    "shortfall_date": null,
    "forecast": [
      {
        "date": "2024-11-01",
        "predicted_balance": 182400.00,
        "lower_80": 178200.00,
        "upper_80": 186600.00,
        "lower_95": 174000.00,
        "upper_95": 190800.00,
        "projected_net_change": -3200.00,
        "scheduled_events": ["Airtel WiFi Bill"]
      }
    ]
  }
  ```

---

## 10. Financial Anomaly Detection (`/anomalies`)

### 10.1 `GET /anomalies`
Fetches all detected anomalies.
- **Query Params:** `is_resolved` (boolean, default false)

### 10.2 `POST /anomalies/scan`
Triggers real-time statistical anomaly scan across recent ledger entries.

### 10.3 `POST /anomalies/{id}/resolve`
Marks anomaly as reviewed or expected with an optional resolution note.

---

## 11. AI Financial Copilot (`/copilot`)

### 11.1 `POST /copilot/query`
Natural language financial advisory with ledger context grounding.
- **Request Body:**
  ```json
  {
    "query": "Can I afford to buy a new smartphone for ₹35,000 this month?"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "answer": "Based on your current financial status, your projected month-end surplus is ₹52,550 after accounting for ₹28,000 in upcoming rent and ₹25,000 in scheduled SIPs. While you technically have the liquidity, spending ₹35,000 would reduce your savings rate from 42% to 14% and delay your 6-month Emergency Fund target by 1.5 months. If you proceed, consider spreading the cost or reducing dining expenses.",
    "provider_used": "groq-llama-3.3-70b",
    "context_citations": {
      "projected_surplus": "₹52,550",
      "current_savings_rate": "42%",
      "emergency_fund_target": "₹3,00,000"
    },
    "suggested_followups": [
      "What are my highest discretionary expenses?",
      "How much do I spend on dining out each month?",
      "Simulate a ₹35,000 expense in the Scenario Simulator"
    ]
  }
  ```

---

## 12. Scenario Simulation (`/simulation`)

### 12.1 `POST /simulation/run`
Simulates "What-If" scenarios over 6, 12, and 24 months.
- **Request Body:**
  ```json
  {
    "income_delta_pct": 10.0,
    "rent_delta_amount": 5000.0,
    "discretionary_reduction_pct": 15.0,
    "new_recurring_monthly": 0.0,
    "lump_sum_amount": 0.0
  }
  ```
- **Response (200 OK):**
  - Baseline vs Simulated trajectory of cumulative savings and net worth.
  - Emergency fund runway differential (e.g. +2.4 months).

---

## 13. Explainable Financial Health Score (`/health-score`)

### 13.1 `GET /health-score`
Detailed breakdown of 0-100 score across 5 mathematical pillars.
- **Response (200 OK):**
  ```json
  {
    "total_score": 82,
    "grade": "Excellent",
    "pillars": [
      {
        "name": "Savings Discipline",
        "score": 18,
        "max_score": 20,
        "current_value": "42.0% savings rate",
        "benchmark": ">= 20% for full score",
        "formula": "min(20, (savings_rate / 20) * 20)",
        "actionable_tip": "Excellent habit! Maintain automated SIP transfers."
      },
      {
        "name": "Emergency Preparedness",
        "score": 16,
        "max_score": 20,
        "current_value": "3.8 months runway",
        "benchmark": "6.0 months target",
        "formula": "min(20, (months_runway / 6.0) * 20)",
        "actionable_tip": "Save ₹1,15,500 more to hit the full 6-month safety net."
      }
    ]
  }
  ```

---

## 14. Admin & ML Diagnostics (`/diagnostics`)

### 14.1 `GET /diagnostics/system-health`
Database connectivity status, response latency, active AI provider mode.

### 14.2 `GET /diagnostics/ml-models`
Classification accuracy, per-class F1 score, confusion matrix data, and forecasting backtest error (RMSE, MAE).

### 14.3 `POST /diagnostics/seed-demo-data`
Re-initializes the Rahul Sharma demo dataset for fresh evaluation.
