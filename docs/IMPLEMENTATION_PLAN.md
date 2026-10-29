# FinPilot AI: Phased Implementation Plan

**Target System:** FinPilot AI - Intelligent Personal Financial Advisor for Indian Users  
**Version:** 1.0.0  

---

## 1. Environment & Pre-requisites Assessment

- **Operating System:** macOS (Darwin arm64)
- **Runtimes:** Python 3.13.5, Node.js v25.7.0, npm 11.10.1
- **Storage/DB:** SQLite for local zero-config testing & PostgreSQL ready via SQLAlchemy 2.0 URL config
- **ML & Data Stack:** `scikit-learn`, `statsmodels`, `pandas`, `numpy`
- **AI Integration:** Groq API (`groq` package / httpx) with deterministic `MockAIProvider` fallback

---

## 2. Risk Matrix & Mitigation Strategies

| Risk | Impact | Likelihood | Mitigation Strategy |
| :--- | :--- | :--- | :--- |
| **Missing Groq API Key** | High | High | Implement Strategy Pattern with `MockAIProvider` producing deterministic, grounded answers based on the user's ledger data. Clear UI badge indicating provider mode. |
| **PostgreSQL Daemon Missing** | Medium | High | SQLAlchemy 2.0 dual dialect support: Default to `sqlite:///./finpilot.db` for instant local execution and automated test isolation, seamlessly switchable to PostgreSQL via `DATABASE_URL`. |
| **Cold-Start ML Model** | Medium | Medium | Seed a pre-trained model artifact and synthetic Indian training dataset (~500 merchant narrations); retain fallback to deterministic Regex Rule Engine if confidence is below threshold. |
| **Bank CSV Format Variations** | High | High | Flexible column mapping wizard with heuristics for standard Indian banks (HDFC, SBI, ICICI, Axis, Kotak) plus manual column dropdown selectors. |
| **Currency & Number Formatting** | Low | Low | Dedicated Indian Numbering utility (`en-IN` standard, Lakhs/Crores, ₹ symbol, handling trailing Dr/Cr in bank statements). |

---

## 3. Phased Implementation Milestones

### Milestone 1: Monorepo Scaffolding, Core Backend & Database Models
- **Goal:** Establish project skeleton, database schema, Alembic migration, and seed the comprehensive Rahul Sharma demo dataset.
- **Files to Create:**
  - `backend/app/core/config.py`, `backend/app/core/security.py`, `backend/app/core/logging.py`, `backend/app/core/exceptions.py`
  - `backend/app/db/session.py`, `backend/app/db/base.py`, `backend/app/db/seed_data.py`
  - `backend/app/models/user.py`, `account.py`, `category.py`, `transaction.py`, `budget.py`, `recurring_rule.py`, `goal.py`, `anomaly.py`, `category_override.py`, `ml_model_metadata.py`
  - `backend/app/schemas/*` (Pydantic v2 schemas for all entities)
  - `backend/alembic.ini`, `backend/alembic/env.py`, initial migration script
  - `backend/requirements.txt`
- **Deliverables & Verification:**
  - Database schema initialized.
  - Running seed script populates 350+ realistic Indian transactions spanning 12 months for Rahul Sharma with categories, accounts, and budgets.
  - Automated test verifying database models, relationships, and seed data integrity.

---

### Milestone 2: Core Backend Services & REST APIs
- **Goal:** Build and verify transaction management, auth, dashboard aggregation, CSV import/export, and SMS parsing.
- **Files to Create:**
  - `backend/app/api/v1/auth.py`, `dashboard.py`, `transactions.py`, `import_export.py`, `sms_parser.py`, `budgets.py`, `recurring.py`, `goals.py`
  - `backend/app/services/auth_service.py`
  - `backend/app/services/transaction_service.py`
  - `backend/app/services/csv_import_service.py` (with SHA-256 deduplication and Indian date parsing)
  - `backend/app/services/sms_parser_service.py` (HDFC, SBI, ICICI, Axis, UPI regex parsers)
  - `backend/app/services/budget_service.py`
  - `backend/app/services/recurring_service.py`
  - `backend/app/services/goal_service.py`
  - `backend/app/services/report_service.py` (CSV and PDF generation)
- **Deliverables & Verification:**
  - FastAPI app starts cleanly with OpenAPI docs at `/docs`.
  - Pytest tests for registration, login, demo-login, transaction filtering, SMS parsing, and CSV deduplication.

---

### Milestone 3: Machine Learning & Analytics Subsystems
- **Goal:** Implement the intelligence engines (Categorizer, Forecaster, Anomaly Detector, Financial Health Score, Scenario Simulator).
- **Files to Create:**
  - `backend/app/ml/categorization_model.py`:
    - Regex rule engine for Indian merchants (Swiggy, Zomato, Blinkit, Zepto, BESCOM, etc.).
    - TF-IDF + Calibrated Classifier trained on Indian financial narrations.
    - User feedback / override learning loop.
  - `backend/app/ml/forecasting_engine.py`:
    - Time-series aggregation, Holt-Winters / ARIMA exponential smoothing, recurring event overlay, 80%/95% confidence intervals, and shortfall risk detection.
  - `backend/app/ml/anomaly_detector.py`:
    - Amount outlier detection (IQR & Z-score per category), duplicate candidate flagging, rolling velocity spend spike detector.
  - `backend/app/services/health_score_service.py`:
    - 5-pillar transparent 0-100 score calculator with mathematical formulas and actionable recommendations.
  - `backend/app/services/simulation_service.py`:
    - Dynamic What-If projection engine for changes in income, rent, discretionary spend, and new EMIs.
  - `backend/app/api/v1/forecasting.py`, `anomalies.py`, `health_score.py`, `simulation.py`, `diagnostics.py`
- **Deliverables & Verification:**
  - Pytest suite testing ML classification accuracy (>85% on test split), forecasting consistency, anomaly detection sensitivity, and health score math.

---

### Milestone 4: AI Financial Copilot Subsystem
- **Goal:** Implement the context-grounded AI Copilot with Groq integration and robust offline deterministic mock provider.
- **Files to Create:**
  - `backend/app/ml/copilot_agent.py`
  - `backend/app/ml/providers/base_provider.py`
  - `backend/app/ml/providers/groq_provider.py`
  - `backend/app/ml/providers/mock_provider.py`
  - `backend/app/api/v1/copilot.py`
- **Deliverables & Verification:**
  - Pytest verifying Copilot queries for affordability checks, spending breakdowns, and advice in both Mock and Live modes with strict grounding in user financial records.

---

### Milestone 5: Frontend Core & Primary Dashboard Views
- **Goal:** Initialize React + Vite + TypeScript + Tailwind CSS application with rich dark-mode aesthetics, Indian currency formatting, and primary financial dashboard.
- **Files to Create:**
  - `frontend/package.json`, `vite.config.ts`, `tailwind.config.js`, `postcss.config.js`, `tsconfig.json`
  - `frontend/src/index.css` (Glassmorphism tokens, custom gradients, scrollbars)
  - `frontend/src/types/index.ts` (Full TypeScript contract matching backend schemas)
  - `frontend/src/api/client.ts` (Axios / Fetch client with JWT interceptor and error handling)
  - `frontend/src/context/AuthContext.tsx`
  - `frontend/src/components/common/*` (Navbar, Sidebar, StatCard, Badge, Modal, EmptyState, LoadingSpinner)
  - `frontend/src/components/dashboard/*` (KPI metrics, Cash Flow Trend chart, Category Donut chart, Recent Transactions list)
  - `frontend/src/pages/DashboardPage.tsx`, `LoginPage.tsx`, `RegisterPage.tsx`
- **Deliverables & Verification:**
  - Clean build with Vite and TypeScript.
  - Responsive, high-contrast dark dashboard connected to backend and seeded data.

---

### Milestone 6: Advanced Frontend Workflows & Visualizations
- **Goal:** Build the interactive feature suite (Transactions & CSV Import Wizard, SMS Sandbox, Forecast Visualizer, Anomaly Feed, AI Copilot, Budget Tracker, What-If Simulator, Health Score radar, and Diagnostics panel).
- **Files to Create:**
  - `frontend/src/components/transactions/TransactionTable.tsx`, `TransactionFilterBar.tsx`, `CsvImportModal.tsx`
  - `frontend/src/components/sms/SmsSandbox.tsx`
  - `frontend/src/components/budgets/BudgetManager.tsx`, `BudgetPacingCard.tsx`
  - `frontend/src/components/recurring/RecurringList.tsx`
  - `frontend/src/components/forecast/ForecastChart.tsx`, `ShortfallAlertCard.tsx`
  - `frontend/src/components/anomalies/AnomalyFeed.tsx`
  - `frontend/src/components/copilot/CopilotDrawer.tsx`, `ChatMessage.tsx`
  - `frontend/src/components/goals/GoalsManager.tsx`, `EmergencyFundMeter.tsx`
  - `frontend/src/components/simulation/ScenarioSimulator.tsx`
  - `frontend/src/components/health/HealthScoreGauge.tsx`, `PillarRadarChart.tsx`
  - `frontend/src/components/diagnostics/ModelInspector.tsx`, `ConfusionMatrix.tsx`
  - Respective Pages in `frontend/src/pages/*`
- **Deliverables & Verification:**
  - Every UI component interacts with live backend endpoints.
  - No fake buttons or mocked UI without real backing logic.

---

### Milestone 7: End-to-End Testing, Polish, and Evaluation Readiness
- **Goal:** Comprehensive automated test verification, documentation synchronization, and presentation readiness.
- **Deliverables & Verification:**
  - Backend test coverage report (`pytest`).
  - Frontend test checks (`npm run build`, `npm run test` or typecheck).
  - Browser verification of key user flows (Demo login, CSV upload, SMS parsing, Copilot chat, Scenario simulation, PDF/CSV export).
  - Complete documentation and clean startup scripts.
