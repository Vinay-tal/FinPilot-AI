# FinPilot AI: Intelligent Personal Financial Advisor for Indian Users
## Comprehensive Requirements Specification

**Version:** 1.0.0  
**Status:** Approved for Implementation Planning  
**Target Audience:** Academic Evaluators (Software Engineering & ML), Indian Salaried & Self-Employed Users  

---

## 1. Executive Summary & Vision

**FinPilot AI** is a production-grade, full-stack personal finance management and advisory platform tailored specifically for Indian users. Traditional personal finance tools fail to address the nuances of the Indian financial ecosystem—such as UPI-based micro-transactions, SMS transaction alerts, diverse bank statement formats (HDFC, SBI, ICICI, Axis, Kotak), distinct recurring payment cycles (SIPs, rent via UPI, domestic utility boards), and financial goal priorities (Emergency Fund, Festival/Travel funds, Tax-efficient savings).

FinPilot AI bridges this gap by combining:
1. **Robust Relational Data Engineering:** Transparent, deduplicated, and audited financial ledger.
2. **Machine Learning & Time-Series Intelligence:** Automated merchant categorization, cash-flow forecasting with uncertainty bands, and statistical anomaly detection.
3. **Explainable AI (XAI) & Financial Copilot:** Contextual financial advisory powered by Groq Llama-3.3 / robust offline mock intelligence with verifiable mathematical proofs for financial health scores and recommendations.
4. **Deterministic Demo & Zero-Friction Evaluation:** Fully seeded synthetic Indian dataset (Rahul Sharma persona, Bengaluru tech professional) allowing immediate end-to-end evaluation without sharing real banking credentials or paying for external API keys.

---

## 2. User Personas

### Persona 1: Rahul Sharma (Primary Persona - Demo User)
- **Age:** 28 | **Location:** Bengaluru, Karnataka
- **Role:** Senior Software Engineer | **Monthly Inhand Salary:** ₹1,25,000 (Credited on 30th/31st)
- **Financial Profile:**
  - High UPI frequency (Swiggy, Blinkit, Zepto, Uber, Chai/Cafe).
  - Monthly fixed obligations: Rent (₹28,000 via UPI), BESCOM/ACT Fibernet (₹2,500), SIP investments (₹25,000 in Zerodha/Groww).
  - Pain Point: Wondering where discretionary income vanishes mid-month; lack of visibility into projected month-end balance.

### Persona 2: Priya Patel (Academic Evaluator Persona)
- **Role:** Computer Science / Data Science Professor or Industry Evaluator.
- **Goal:** Verify software architecture rigor, ML model training & evaluation metrics (F1 score, confusion matrix, RMSE), API documentation, data validation, test coverage, and safety compliance.

---

## 3. Functional Requirements (FR)

### FR-1: Secure Authentication & User Session Management
- **FR-1.1:** Secure registration with email, full name, currency preference (default: `INR / ₹`), and password.
- **FR-1.2:** Password hashing using industry-standard `bcrypt` with work factor >= 12.
- **FR-1.3:** JWT-based bearer authentication (access token with configurable expiry, e.g. 60 mins).
- **FR-1.4:** Protected API routes verifying token validity, user activation state, and tenant isolation.
- **FR-1.5:** Demo User Quick-Login button allowing instantaneous evaluation without manual signup.

### FR-2: Financial Dashboard & Metrics Engine
- **FR-2.1:** Real-time computation of core metrics for selected period (Current Month, Last 30 Days, Last 90 Days, Year-to-Date):
  - Total Inflow (Income & Credits).
  - Total Outflow (Expenses & Debits).
  - Net Savings & Savings Rate (`(Income - Expenses) / Income * 100`).
  - Account Balances breakdown (Bank Accounts, Credit Cards, Investment Wallets).
- **FR-2.2:** Dynamic visualizations:
  - Monthly Cash Flow Trend (Income vs Expense bar/line chart).
  - Category Breakdown (Interactive Donut chart with Indian category taxonomy).
  - Daily cumulative spending trajectory compared against budget pace.
- **FR-2.3:** Recent Transactions table with real-time text search, category filtering, and sorting.

### FR-3: Bank Statement CSV Importer with Mapping Wizard
- **FR-3.1:** Multi-bank statement ingestion supporting standard formats:
  - HDFC Bank, State Bank of India (SBI), ICICI Bank, Axis Bank, Kotak Mahindra Bank, and Generic CSV.
- **FR-3.2:** Interactive Column Mapping Wizard:
  - Auto-detection and manual overrides for: `Date`, `Description/Narration`, `Debit/Withdrawal`, `Credit/Deposit`, `Balance`, `Reference/Cheque Number`.
- **FR-3.3:** Robust Data Sanitization:
  - Parsing Indian date conventions (`DD/MM/YYYY`, `DD-MM-YYYY`, `YYYY-MM-DD`, `DD-Mon-YYYY`).
  - Handling Indian numeric formatting (e.g. `1,25,000.50`, trailing `Dr`/`Cr`).
- **FR-3.4:** Deduplication Engine:
  - SHA-256 fingerprinting based on `(user_id, date, amount, transaction_type, normalized_narration)`.
  - Detection and prevention of duplicate transaction entries across repeated uploads.
- **FR-3.5:** Staging & Interactive Preview:
  - User reviews parsed transactions, detected duplicates, and predicted categories before confirming ledger commit.

### FR-4: Indian Bank SMS Transaction Parser
- **FR-4.1:** Regex and rule-based parser handling standard Indian bank transactional SMS formats:
  - **HDFC:** `Sent Rs.550.00 from HDFC Bank A/C *4821 to Swiggy on 14-OCT-24. UPI: 428719283741.`
  - **SBI:** `Dear SBI User, A/C 9812 debited by Rs 1,200.00 on 12Oct24 transfer to Zomato Ref No 4291823719.`
  - **ICICI:** `Acct XX102 debited for Rs 350.00 on 10-Oct-24; UPI/429182/Blinkit. Call 1800... if not you.`
  - **Axis / Kotak / PhonePe / Google Pay / Paytm notifications.**
- **FR-4.2:** Extraction fields: `Amount`, `Currency`, `Type (Debit/Credit)`, `Merchant/Beneficiary`, `Account Last 4`, `Date`, `Reference/UPI Ref`.
- **FR-4.3:** In-app SMS Sandbox:
  - Paste any transactional SMS text or select from realistic presets to inspect instantaneous parsing into structured JSON and test accuracy.

### FR-5: Intelligent Auto-Categorization (Rule Engine + Machine Learning)
- **FR-5.1:** Indian Merchant Rule Engine:
  - Fast-path deterministic regex/substring matching for 100+ prominent Indian merchants:
    - *Food & Dining:* Swiggy, Zomato, McDonald's, Chai Point, Starbucks, Haldirams.
    - *Groceries & Essentials:* Blinkit, Zepto, Instamart, BigBasket, D-Mart, Nature's Basket.
    - *Transportation:* Uber, Ola, Rapido, Namma Metro, IRCTC, Shell, Indian Oil.
    - *Utilities & Telecom:* BESCOM, MSEDCL, Tata Power, Airtel, Jio, ACT Fibernet.
    - *Shopping & E-commerce:* Amazon, Flipkart, Myntra, Nykaa, Ajio, Tata CliQ.
    - *Investments & Wealth:* Zerodha, Groww, CAMS, Kuvera, Angel One.
    - *Entertainment & Subs:* Netflix, Spotify, BookMyShow, Disney+ Hotstar, Cult.fit.
    - *Income:* Salary, Interest Credit, Dividend, Refunds.
- **FR-5.2:** Machine Learning Text Classifier:
  - Feature extraction: TF-IDF vectorizer (unigrams + bigrams, sublinear TF scaling).
  - Classification Model: Calibrated Multinomial Naive Bayes / Logistic Regression / LinearSVC with probability estimates.
  - Returns predicted category and confidence score `[0.0, 1.0]`.
- **FR-5.3:** Hybrid Arbiter & Human Feedback:
  - Rule match -> 1.0 confidence.
  - ML confidence >= 0.70 -> Assigned automatically with `ml_predicted` badge.
  - ML confidence < 0.70 -> Assigned `Needs Review` / default category with top-3 alternative suggestions.
  - When user modifies a category, system saves user-specific override and triggers model training sample ingestion.

### FR-6: Budget Management & Real-Time Pacing
- **FR-6.1:** Monthly category-level budgets and global monthly expense ceilings.
- **FR-6.2:** Real-time spend tracking:
  - Amount spent, remaining allowance, percentage consumed.
  - Pacing indicator: Calculates projected month-end spend based on elapsed days vs total days in month.
- **FR-6.3:** Visual alerts:
  - Safe (`< 75%`), Warning (`75% - 99%`), Exceeded (`>= 100%`).

### FR-7: Recurring Expense & Subscription Detection
- **FR-7.1:** Algorithmic periodicity detector analyzing transaction clusters by merchant/narration and amount variance (< 10%).
- **FR-7.2:** Cadence identification: Weekly, Bi-weekly, Monthly, Quarterly, Annual.
- **FR-7.3:** Output catalog:
  - Recurring name, category, average amount, last billing date, next projected billing date, status (Active / Dormant / Cancelled).
- **FR-7.4:** Detection of unwanted or duplicate subscriptions (e.g. concurrent streaming platforms).

### FR-8: Time-Series Cash Flow Forecasting & Shortfall Warnings
- **FR-8.1:** Forward-looking cash flow and bank balance projection for 30 to 90 days.
- **FR-8.2:** Modeling methodology:
  - Baseline: Holt-Winters Exponential Smoothing / ARIMA from `statsmodels`.
  - Incorporates detected recurring bills and expected salary credits at known day-of-month intervals.
  - Generates 80% and 95% confidence intervals (prediction cones).
- **FR-8.3:** Liquidity Shortfall Warning:
  - Flag exact projected date where bank balance drops below emergency minimum safety threshold (e.g. ₹10,000 or user buffer).

### FR-9: Financial Anomaly Detection Engine
- **FR-9.1:** Statistical Outlier Detection:
  - Category-based IQR (Interquartile Range) and Z-Score (> 2.5 sigma) to flag unusually large transactions.
- **FR-9.2:** Duplicate Transaction Detection:
  - Identifies transactions with identical amount and merchant occurring within 48 hours.
- **FR-9.3:** Category Spike Detection:
  - Trailing 7-day spend exceeding 2.5x historical rolling weekly mean.
- **FR-9.4:** Actionable Anomaly Feed:
  - Detailed explanation card for each anomaly, with one-click "Acknowledge / Expected" or "Flag for Review".

### FR-10: AI Financial Copilot (RAG over Personal Financial Ledger)
- **FR-10.1:** Chat interface embedded within the application.
- **FR-10.2:** Retrieval-Augmented Generation (RAG):
  - Injects aggregated user financial context into LLM prompt (current month totals, top category spends, budget utilization, recurring commitments, anomaly alerts).
- **FR-10.3:** Multi-Provider Architecture:
  - Primary: Groq API (`llama-3.3-70b-versatile` or `llama-3.1-8b-instant`).
  - Built-in Mock AI Provider: Deterministic, data-grounded advisor with high-quality natural language generation matching queries (spending queries, afford-it checks, savings tips) for offline testing without API keys.
- **FR-10.4:** Strict Grounding & Privacy:
  - Guardrails preventing hallucination; cites exact numbers from the user's ledger.
  - Zero PII (no account numbers or sensitive credentials) transmitted.

### FR-11: Savings Goals, Emergency Fund & Expense Reduction
- **FR-11.1:** Goal tracker with Target Amount, Target Date, Current Balance, and calculated Monthly Savings required.
- **FR-11.2:** Emergency Fund Assessment:
  - Computes mandatory living expenses (Rent + Groceries + Utilities + Minimum Debt).
  - Recommends 3-month (conservative) and 6-month (resilient) reserve targets in INR.
  - Displays current months of runway.
- **FR-11.3:** Expense Reduction Recommender:
  - Pinpoints top 3 discretionary leakage areas and calculates potential annual savings (e.g., cutting Swiggy orders by 25% saves ₹36,000/year).

### FR-12: Interactive "What-If" Scenario Simulator
- **FR-12.1:** Dynamic simulation parameters:
  - Income change percentage (increment, promotion, job change, side hustle).
  - Fixed cost change (rent increase, new flat).
  - Discretionary spending reduction (-10%, -20%, -30%).
  - New recurring obligation (e.g. Car EMI, Laptop purchase).
  - One-time lump sum expense or windfall.
- **FR-12.2:** Real-time projection over 6, 12, and 24 months:
  - Impact on Net Savings, Emergency Fund Runway, and Goal Completion Dates.
  - Side-by-side comparative visualization (Baseline vs Simulated).

### FR-13: Explainable Financial Health Score (0 - 100)
- **FR-13.1:** 5 Transparent Pillars (20 points each, sum = 100):
  1. *Savings Discipline (20 pts):* Based on savings rate (20% savings = 20 pts; linear scaling below).
  2. *Spending Control (20 pts):* Adherence to budget limits and non-essential spend ratio.
  3. *Emergency Preparedness (20 pts):* Liquid reserves covering >= 3 months mandatory expenses.
  4. *Cash Flow Stability (20 pts):* Consistently positive net cash flow over trailing 3-6 months.
  5. *Debt & Fixed Load (20 pts):* Fixed obligations < 50% of net monthly income.
- **FR-13.2:** Transparent Math: Display exact formulas, user values, benchmark thresholds, and actionable steps to earn remaining points in each pillar.

### FR-14: Comprehensive Reports & Export (CSV & PDF)
- **FR-14.1:** Clean CSV export of filtered transaction ledgers.
- **FR-14.2:** Executive PDF Financial Health Summary Report:
  - Formatted multi-section document with key financial KPIs, category distribution, budget health, score breakdown, and personalized recommendations.

### FR-15: Seeded Indian Demo Dataset
- **FR-15.1:** Pre-populated realistic financial history for Rahul Sharma (350+ transactions across 12 months).
- **FR-15.2:** Pre-configured budgets, recurring subscriptions, savings goals, and synthetic anomalies.
- **FR-15.3:** "Reset Demo Data" option in Settings to re-seed initial clean state anytime.

### FR-16: Admin / Diagnostics & Model Evaluation Panel
- **FR-16.1:** System Diagnostics: API latency, Database connectivity, Active AI Provider mode (Groq vs Mock).
- **FR-16.2:** Machine Learning Inspector:
  - Classification metrics: Precision, Recall, F1-Score per category, overall accuracy.
  - Interactive Confusion Matrix.
  - Top informative TF-IDF keywords per category.
  - Model retrain trigger with test evaluation split.
- **FR-16.3:** Time Series & Anomaly Diagnostics:
  - Backtest metrics (MAE, RMSE) for forecasting.
  - Distribution and z-score threshold visualizer.

---

## 4. Non-Functional Requirements (NFR)

- **NFR-1 (Performance):** Dashboard queries compute in `< 100ms` for up to 10,000 transactions per user; ML inference `< 15ms` per batch.
- **NFR-2 (Security):** Secure password hashing (`bcrypt`), JWT Bearer tokens, CORS origin restrictions, parameterized SQL queries via SQLAlchemy (zero SQL injection).
- **NFR-3 (Reliability & Portability):** Zero external paid service dependency required to run in full fidelity (Mock AI + SQLite default with instant switch to PostgreSQL).
- **NFR-4 (Explainability):** No "black-box" scores. All scores, forecasts, and anomalies provide human-readable math and rationale.
- **NFR-5 (Usability & Design):** World-class dark-mode optimized aesthetic with Tailwind CSS, custom HSL color palette, smooth micro-interactions, responsive on desktop and tablets.
- **NFR-6 (Code Quality & Testability):** Typed Python with Pydantic v2 and TypeScript strict mode. Full automated test suite (pytest + vitest).
