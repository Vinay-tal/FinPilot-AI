# FinPilot AI: System Architecture Document

**Version:** 1.0.0  
**Stack:** Python 3.11+ / FastAPI / SQLAlchemy 2.x / Pydantic v2 / React 18 / TypeScript / Vite / Tailwind CSS  

---

## 1. Architectural Overview & Monorepo Layout

FinPilot AI follows a clean, modular **Layered Clean Architecture** adhering to Separation of Concerns (SoC) and the Single Responsibility Principle (SRP). The project is structured as a monorepo with cleanly decoupled frontend and backend domains:

```
finpilot-ai/
├── backend/
│   ├── app/
│   │   ├── api/             # FastAPI routers (Endpoints, route-level validation, deps)
│   │   │   ├── v1/
│   │   │   │   ├── auth.py
│   │   │   │   ├── dashboard.py
│   │   │   │   ├── transactions.py
│   │   │   │   ├── import_export.py
│   │   │   │   ├── sms_parser.py
│   │   │   │   ├── budgets.py
│   │   │   │   ├── recurring.py
│   │   │   │   ├── forecasting.py
│   │   │   │   ├── anomalies.py
│   │   │   │   ├── copilot.py
│   │   │   │   ├── goals.py
│   │   │   │   ├── simulation.py
│   │   │   │   ├── health_score.py
│   │   │   │   └── diagnostics.py
│   │   ├── core/            # Configuration, security, exceptions, logging, database session
│   │   │   ├── config.py
│   │   │   ├── security.py
│   │   │   ├── exceptions.py
│   │   │   ├── logging.py
│   │   │   └── deps.py
│   │   ├── db/              # Database setup, base model, seeds, and migrations
│   │   │   ├── session.py
│   │   │   ├── base.py
│   │   │   └── seed_data.py
│   │   ├── models/          # SQLAlchemy 2.0 ORM Declarative Models
│   │   │   ├── user.py
│   │   │   ├── account.py
│   │   │   ├── category.py
│   │   │   ├── transaction.py
│   │   │   ├── budget.py
│   │   │   ├── recurring_rule.py
│   │   │   ├── goal.py
│   │   │   └── anomaly.py
│   │   ├── schemas/         # Pydantic v2 validation and serialization schemas
│   │   ├── services/        # Pure Business Logic Layer
│   │   │   ├── auth_service.py
│   │   │   ├── transaction_service.py
│   │   │   ├── csv_import_service.py
│   │   │   ├── sms_parser_service.py
│   │   │   ├── budget_service.py
│   │   │   ├── recurring_service.py
│   │   │   ├── health_score_service.py
│   │   │   ├── goal_service.py
│   │   │   ├── simulation_service.py
│   │   │   └── report_service.py
│   │   └── ml/              # Machine Learning, Statistical & AI Models
│   │       ├── categorization_model.py   # TF-IDF + Classifier & Rule Engine
│   │       ├── forecasting_engine.py     # Time-series forecasting (statsmodels)
│   │       ├── anomaly_detector.py       # IQR, Z-Score, rolling window detector
│   │       ├── copilot_agent.py          # RAG context builder + LLM provider
│   │       └── providers/                # Strategy pattern for LLM
│   │           ├── base_provider.py
│   │           ├── groq_provider.py
│   │           └── mock_provider.py
│   ├── tests/               # Pytest suite (unit, integration, ML evaluation)
│   │   ├── conftest.py
│   │   ├── test_auth.py
│   │   ├── test_transactions.py
│   │   ├── test_categorization.py
│   │   ├── test_forecasting.py
│   │   ├── test_sms_parser.py
│   │   └── test_health_score.py
│   ├── alembic/             # Database migration scripts
│   ├── alembic.ini
│   ├── requirements.txt
│   └── main.py              # Application entrypoint
├── frontend/
│   ├── src/
│   │   ├── api/             # Typed API client, Axios/Fetch hooks
│   │   ├── assets/
│   │   ├── components/      # UI components (shadcn/ui style, atomic, accessible)
│   │   │   ├── common/      # Navbar, Sidebar, Modal, Toast, StatCard, Badge
│   │   │   ├── dashboard/   # Financial Overview, Cashflow charts, Metric cards
│   │   │   ├── transactions/# Transaction table, Filter bar, CSV Import Wizard
│   │   │   ├── sms/         # SMS Parser Sandbox & batch tester
│   │   │   ├── budgets/     # Budget cards, Pacing bars, category limits
│   │   │   ├── recurring/   # Subscriptions & bills list, cycle indicators
│   │   │   ├── forecast/    # Forecasting chart with uncertainty bands, shortfall alert
│   │   │   ├── anomalies/   # Anomaly feed, dismiss/review triggers
│   │   │   ├── copilot/     # AI Copilot chat drawer/panel with query chips
│   │   │   ├── goals/       # Savings goals, emergency fund runway meter
│   │   │   ├── simulation/  # Scenario simulator with real-time sliders
│   │   │   ├── health/      # Health score gauge, pillar breakdown radar
│   │   │   └── diagnostics/ # ML performance, confusion matrix, system health
│   │   ├── context/         # AuthContext, ThemeContext, DemoContext
│   │   ├── hooks/           # Custom React hooks (useDashboard, useTransactions, etc.)
│   │   ├── lib/             # Utility functions, currency formatters (INR ₹)
│   │   ├── types/           # TypeScript interfaces matching backend Pydantic schemas
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css        # Tailwind CSS + custom glassmorphic tokens
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── docs/                    # Architectural and project documentation
├── scripts/                 # Utility scripts (seed_db, train_model, run_checks)
├── ARCHITECTURE.md
├── REQUIREMENTS.md
├── DATABASE_DESIGN.md
├── API_SPEC.md
└── IMPLEMENTATION_PLAN.md
```

---

## 2. Backend Design: Layered Architecture

```mermaid
graph TD
    Client["Frontend (React / Vite)"] -->|HTTPS / JSON / JWT| API["FastAPI Router Layer (/api/v1/*)"]
    API -->|Schema Validation| Pydantic["Pydantic v2 Request / Response Schemas"]
    API -->|Invoke| Service["Service Layer (Business Logic)"]
    Service -->|Query / Mutate| ORM["SQLAlchemy 2.0 ORM Repositories"]
    ORM -->|Connection Pool| DB[("Relational Database: SQLite (Dev) / PostgreSQL (Prod)")]
    Service -->|Inference & Prediction| ML["Machine Learning & Analytics Subsystem"]
    ML --> Cat["TF-IDF + Calibrated Classifier (Categorization)"]
    ML --> Forecast["Statsmodels Exponential Smoothing / ARIMA (Forecast)"]
    ML --> Anomaly["Statistical IQR / Z-Score Engine (Anomalies)"]
    Service -->|Contextual RAG Query| Copilot["AI Copilot Subsystem"]
    Copilot --> ProviderChooser{"GROQ_API_KEY Available?"}
    ProviderChooser -->|Yes| Groq["Groq API (Llama-3.3-70b / 3.1-8b)"]
    ProviderChooser -->|No| MockAI["Deterministic High-Fidelity Mock Advisor"]
```

### 2.1 Dependency Injection & Security
- FastAPI's `Depends(get_current_user)` validates incoming JWT tokens on every protected endpoint.
- Database sessions are provided through an asynchronous/context-managed generator `get_db()`, guaranteeing proper commit/rollback transaction semantics.
- Tenant isolation: All database queries enforce filtering on `user_id = current_user.id`.

### 2.2 Relational Database Portability
- Built on SQLAlchemy 2.0 declarative models using standard ANSI SQL types (`String`, `Numeric(12, 2)`, `DateTime`, `Boolean`, `ForeignKey`).
- Default development connection: `sqlite:///./finpilot.db` (enables zero-config running on any machine with zero external daemons).
- Production connection: Configurable via `DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/finpilot`.

---

## 3. Machine Learning & Analytical Subsystems

### 3.1 Transaction Categorization Engine
- **Strategy:** Two-Tier Hybrid Architecture (Rule Engine + Supervised ML).
- **Tier 1 (Deterministic Rule Engine):** Matches against curated Indian merchant regexes (e.g. `r"UPI.*(SWIGGY|ZOMATO|BLINKIT)"i`). If matched, returns category with `confidence = 1.0` and `method = "rule"`.
- **Tier 2 (Supervised NLP Classifier):**
  - Text Pipeline: Lowercasing, punctuation stripping, Indian UPI ID and reference number normalization (e.g., replaces reference digits with `<NUM>` token).
  - Feature Extractor: `TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True)`.
  - Classifier: `LogisticRegression(class_weight='balanced', max_iter=1000)` or `CalibratedClassifierCV(LinearSVC())` for probabilistic confidence estimation.
  - Evaluation: Measured via Stratified K-Fold Cross Validation (Precision, Recall, F1-Score).
- **Feedback & Continual Learning:** User category overrides are persisted in `category_overrides` and incorporated into periodic model retraining.

### 3.2 Time-Series Cash Flow Forecasting
- **Engine:** `statsmodels.tsa.holtwinters.ExponentialSmoothing` combined with deterministic scheduled recurring event injection.
- **Workflow:**
  1. Aggregates daily net cash flows over trailing 90-180 days.
  2. Applies trend and seasonality smoothing.
  3. Overlays deterministic detected recurring transactions (e.g. known Salary on day 30, known Rent on day 1).
  4. Computes prediction standard error to derive 80% and 95% confidence bands.
  5. Scans forward trajectory for zero-crossing or breach of user minimum safety buffer, returning proactive shortfall alert with exact estimated date and severity.

### 3.3 Multi-Criteria Anomaly Detection
1. **IQR & Z-Score Amount Outliers:** Computes median and IQR per category for the user. Flags transactions where:
   $$\text{Amount} > Q_3 + 2.5 \times \text{IQR} \quad \text{or} \quad z = \frac{\text{Amount} - \mu_{\text{category}}}{\sigma_{\text{category}}} > 2.5$$
2. **Duplicate Ingestion Flagger:** Identifies transactions with matching absolute amount and merchant within a 48-hour window.
3. **Rolling Velocity Spikes:** Detects when rolling 7-day spend in any category exceeds 250% of the 30-day baseline.

### 3.4 AI Copilot & Strategy Pattern
- **Base Interface (`BaseLLMProvider`):** Defines `generate_financial_advice(query: str, financial_context: FinancialContext) -> CopilotResponse`.
- **Groq Provider:** Calls Groq Cloud API with streaming/REST, using system prompt tailored with user's financial telemetry.
- **Deterministic Mock Provider:** Built-in offline engine parsing query intent (Affordability check, Spending summary, Savings advice, Score explanation) and producing data-grounded answers citing the user's exact numbers.

---

## 4. Frontend Architecture

### 4.1 State & Component Design
- **Core Framework:** React 18 with TypeScript in strict mode.
- **Styling:** Vanilla Tailwind CSS with a curated, high-contrast dark theme:
  - Deep Navy / Slate background (`#0b0f19`, `#111827`)
  - Accent Emerald for Positive/Savings (`#10b981`), Amber for Warnings (`#f59e0b`), Rose for Expenses/Alerts (`#f43f5e`), Electric Cyan for AI/Copilot (`#06b6d4`).
- **Data Visualization:** Recharts (responsive container, custom tooltips with INR formatting, smooth animation curves).
- **Component Breakdown:**
  - `Navbar` & `Sidebar`: Collapsible, active route indicator, Quick Demo Switch, User Avatar.
  - `FinancialHealthWidget`: Animated circular/arc gauge showing score (0-100) with drill-down radar chart.
  - `CashflowForecaster`: Area/Line chart with shaded confidence interval and shortfall trigger flag.
  - `ImportWizard`: Drag-and-drop CSV upload, column auto-map dropdowns, validation badge, staged commit table.
  - `SmsParserSandbox`: Live text input, parsed JSON inspector, instant batch tester.
  - `ScenarioSimulator`: Range sliders for Income, Rent, Discretionary Spend; dynamic before-and-after projections.
  - `CopilotChat`: Side-drawer assistant with suggested prompts ("Can I afford an iPhone 16?", "Where did I overspend?").

---

## 5. Security & Privacy Architecture

1. **Authentication Security:**
   - Passwords hashed using `bcrypt` (12 rounds).
   - JWT tokens signed with HMAC-SHA256 and secret key configured via environment variables.
2. **Data Isolation:**
   - Multi-tenant architecture at table level: every financial record possesses a `user_id` foreign key.
   - All repository and service queries strictly filter by the authenticated user's ID.
3. **No Credential Exposure:**
   - The system never asks for or stores net banking passwords, PINs, OTPs, or CVVs.
   - Bank SMS parsing works purely on notification text without requiring Android SMS read permissions or access to phone hardware.
4. **AI Safety & Privacy:**
   - Copilot RAG passes only anonymized summary metrics (totals, category percentages, merchant aggregates) to LLMs—never raw personal identifiers or bank account numbers.

---

## 6. Resilience & Error Handling

- **Global Exception Handlers:** FastAPI exception handler capturing `AppException`, `ValidationError`, and unhandled errors, returning standard RFC 7807 problem details:
  ```json
  {
    "error_code": "RESOURCE_NOT_FOUND",
    "message": "Transaction with ID 42 was not found.",
    "details": {}
  }
  ```
- **Frontend Error Boundaries:** Gracefully catch rendering errors and display friendly retry screens without crashing the whole application.
- **Graceful Degradation:** If the ML model is not yet trained, the system seamlessly falls back to rule-based categorization. If Groq API is unreachable or unconfigured, it transparently uses the deterministic Mock AI Advisor with a clear UI status indicator.
