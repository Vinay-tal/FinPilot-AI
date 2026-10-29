export interface User {
  id: string
  email: string
  full_name: string
  currency: string
  is_active: boolean
  is_demo: boolean
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

export interface FinancialAccount {
  id: string
  user_id: string
  name: string
  account_type: 'SAVINGS' | 'CURRENT' | 'CREDIT_CARD' | 'INVESTMENT' | 'WALLET'
  institution: string
  account_number_mask?: string
  balance_paise: number
  balance_inr: number
  currency: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TransactionCategory {
  id: string
  name: string
  slug: string
  icon: string
  color: string
  is_income: boolean
  is_system: boolean
  user_id?: string
  created_at: string
}

export interface Transaction {
  id: string
  user_id: string
  account_id: string
  category_id: string
  category_name?: string
  category_color?: string
  account_name?: string
  date: string
  amount_paise: number
  amount_inr: number
  transaction_type: 'DEBIT' | 'CREDIT'
  narration: string
  raw_narration?: string
  merchant_name?: string
  payment_mode: 'UPI' | 'NET_BANKING' | 'DEBIT_CARD' | 'CREDIT_CARD' | 'CHEQUE' | 'CASH'
  reference_id?: string
  is_recurring: boolean
  fingerprint: string
  categorization_method: string
  categorization_confidence?: number
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  limit: number
  total_pages: number
}

export interface Budget {
  id: string
  user_id: string
  category_id: string
  category_name?: string
  category_color?: string
  month: number
  year: number
  amount_paise: number
  amount_inr: number
  alert_threshold: number
  spent_paise: number
  spent_inr: number
  remaining_paise: number
  remaining_inr: number
  pacing_pct: number
  alert_status: 'NORMAL' | 'WARNING' | 'EXCEEDED'
  created_at: string
  updated_at: string
}

export interface SavingsGoal {
  id: string
  user_id: string
  name: string
  target_amount_paise: number
  target_amount_inr: number
  current_amount_paise: number
  current_amount_inr: number
  target_date: string
  category: 'EMERGENCY_FUND' | 'VACATION' | 'PURCHASE' | 'INVESTMENT' | 'OTHER'
  priority: 'HIGH' | 'MEDIUM' | 'LOW'
  status: 'IN_PROGRESS' | 'COMPLETED' | 'PAUSED'
  monthly_contribution_paise?: number
  monthly_contribution_inr?: number
  required_monthly_inr?: number
  projected_completion_date?: string
  is_achievable?: boolean
  feasibility_status?: string
  variance_months?: number
  cashflow_strain_warning?: string
  progress_pct: number
  created_at: string
  updated_at: string
}

export interface RecurringTransaction {
  id: string
  user_id: string
  category_id: string
  category_name?: string
  category_color?: string
  name: string
  merchant_name: string
  expected_amount_paise: number
  expected_amount_inr: number
  frequency: 'DAILY' | 'WEEKLY' | 'BIWEEKLY' | 'MONTHLY' | 'QUARTERLY' | 'YEARLY'
  last_detected_date?: string
  next_expected_date: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface FinancialInsight {
  id: string
  user_id: string
  insight_type: 'ANOMALY' | 'SPENDING_SPIKE' | 'BUDGET_ALERT' | 'SAVINGS_TIP' | 'SHORTFALL_WARNING'
  severity: 'INFO' | 'WARNING' | 'CRITICAL'
  title: string
  description: string
  metadata_json?: string
  is_read: boolean
  is_resolved: boolean
  created_at: string
}

export interface DashboardSummary {
  period: string
  total_income_paise: number
  total_income_inr: number
  total_expenses_paise: number
  total_expenses_inr: number
  net_savings_paise: number
  net_savings_inr: number
  savings_rate: number
  total_liquid_balance_paise: number
  total_liquid_balance_inr: number
  total_debt_balance_paise: number
  total_debt_balance_inr: number
  accounts_count: number
  transactions_count: number
  health_score: number
  health_grade: string
  recent_transactions: Transaction[]
}

export interface CashflowTrendItem {
  month: string
  income_paise: number
  expenses_paise: number
  net_paise: number
  income_inr: number
  expenses_inr: number
  net_inr: number
}

export interface CategorySpendItem {
  category_id: string
  category_name: string
  category_color: string
  spent_paise: number
  spent_inr: number
  percentage: number
}

export interface ForecastPoint {
  date: string
  display_date?: string
  balance_inr: number
  lower_bound_inr: number
  upper_bound_inr: number
  lower_bound_95_inr?: number
  upper_bound_95_inr?: number
  discretionary_burn_inr?: number
  recurring_net_inr?: number
  event_name?: string
  is_historical?: boolean
}

export interface HistoricalPoint {
  date: string
  display_date: string
  balance_inr: number
  is_historical: boolean
}

export interface ShortfallRiskInfo {
  shortfall_detected: boolean
  shortfall_date?: string | null
  min_projected_balance_inr: number
  risk_level: string
  shortfall_probability_pct: number
  probability_calibrated: boolean
  days_until_shortfall?: number | null
  buffer_deficit_inr: number
  reserve_threshold_inr: number
}

export interface DriverItem {
  factor: string
  impact_inr: number
  description: string
}

export interface ForecastExplanation {
  summary_narrative: string
  observed_facts: string[]
  assumptions: string[]
  positive_drivers: DriverItem[]
  negative_drivers: DriverItem[]
}

export interface CategoryForecastItem {
  category_id: string
  category_name: string
  category_slug: string
  category_color: string
  current_spent_inr: number
  projected_remaining_inr: number
  projected_month_end_inr: number
  daily_run_rate_inr: number
  pacing_status: 'ON_TRACK' | 'ELEVATED' | 'UNDER_PACING' | string
  pacing_ratio: number
  historical_90d_total_inr: number
}

export interface ForecastResponse {
  horizon_days: number
  model_version?: string
  is_sparse_history?: boolean
  current_balance_inr: number
  projected_end_balance_inr: number
  net_projected_change_inr: number
  daily_burn_rate_inr?: number
  shortfall_detected: boolean
  shortfall_date?: string
  min_projected_balance_inr: number
  risk_analysis?: ShortfallRiskInfo
  explanation?: ForecastExplanation
  forecast_points: ForecastPoint[]
  historical_points?: HistoricalPoint[]
  category_forecasts?: CategoryForecastItem[]
}

export interface ForecastEvaluationResponse {
  status: string
  model_version: string
  evaluated_at: string
  data_coverage_days: number
  walk_forward_splits: number
  test_window_days: number
  baseline: {
    name: string
    mae_inr: number
    rmse_inr: number
  }
  advanced_model: {
    name: string
    mae_inr: number
    rmse_inr: number
  }
  improvement_pct: number
  recommended_model: string
}

export interface StressScenarioResponse {
  scenario_type: string
  shock_description: string
  horizon_days: number
  baseline_end_balance_inr: number
  stressed_end_balance_inr: number
  delta_end_balance_inr: number
  baseline_min_balance_inr: number
  stressed_min_balance_inr: number
  shortfall_induced: boolean
  stressed_shortfall_date?: string | null
  stressed_probability_pct: number
  stressed_risk_level: string
  comparison_points: {
    date: string
    display_date: string
    baseline_balance_inr: number
    stressed_balance_inr: number
    event_name?: string | null
  }[]
}

export interface TrajectoryPoint {
  month_index: number
  month_label: string
  baseline_savings_inr: number
  simulated_savings_inr: number
  differential_inr: number
}

export interface SimulationResponse {
  monthly_baseline_savings_inr: number
  monthly_simulated_savings_inr: number
  monthly_differential_inr: number
  annual_savings_impact_inr: number
  runway_impact_months: number
  trajectory: TrajectoryPoint[]
}

export interface ChatMessage {
  id: string
  role: 'USER' | 'ASSISTANT' | 'SYSTEM'
  content: string
  provider_used?: string
  citations?: CitationItem[]
  facts_vs_estimates?: FactsVsEstimates
  scenario_card?: ScenarioCard | null
  created_at: string
}

export interface ConversationItem {
  id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  last_message_preview: string
}

export interface CitationItem {
  source: string
  title: string
  value: string
  detail: string
}

export interface FactsVsEstimates {
  retrieved_facts: string[]
  model_estimates: string[]
  hypothetical_scenarios: string[]
}

export interface ScenarioCard {
  type: 'AFFORDABILITY' | 'SPENDING_REDUCTION' | 'SAVINGS_HORIZON' | string
  title: string
  verdict?: string
  badge?: string
  verdict_title?: string
  current_liquid_inr?: number
  post_purchase_min_dip_inr?: number
  reserve_threshold_inr?: number
  recommendation?: string
  target_reduction_inr?: number
  projected_monthly_savings_inr?: number
  projected_savings_rate_pct?: number
  allocation?: Array<{
    category_name: string
    current_spent_inr: number
    recommended_cut_inr: number
    target_spent_inr: number
    action_tip?: string
  }>
  months?: number
  baseline_cumulative_inr?: number
  optimized_cumulative_inr?: number
  additional_wealth_inr?: number
  progression?: Array<{
    month_index: number
    month_label: string
    baseline_savings_inr: number
    optimized_savings_inr: number
    wealth_differential_inr: number
  }>
}

export interface CopilotTurnResponse {
  conversation_id: string
  message_id: string
  answer: string
  provider_used: string
  citations: CitationItem[]
  facts_vs_estimates: FactsVsEstimates
  scenario_card?: ScenarioCard | null
  suggested_followups: string[]
}

export interface CopilotResponse {
  answer: string
  provider_used: string
  citations: Record<string, string>
  suggested_followups: string[]
}

// Milestone 3: Ingestion & Transaction Intelligence Types

export interface CSVPreviewRow {
  row_number: number
  raw_date?: string
  parsed_date?: string
  narration?: string
  raw_debit?: string
  raw_credit?: string
  amount_inr?: number
  tx_type?: 'DEBIT' | 'CREDIT'
  balance_inr?: number
  is_duplicate?: boolean
  has_error?: boolean
  error_message?: string
}

export interface CSVPreviewResponse {
  filename: string
  encoding: string
  total_detected_rows: number
  headers: string[]
  suggested_mapping: {
    date_col?: string | null
    narration_col?: string | null
    debit_col?: string | null
    credit_col?: string | null
    amount_col?: string | null
    balance_col?: string | null
  }
  sample_rows: Record<string, string>[]
  parsed_preview_rows: CSVPreviewRow[]
  preview_rows?: CSVPreviewRow[]
  potential_duplicates: number
}

export interface CSVImportResult {
  status: string
  job_id: string
  total_rows: number
  imported_rows: number
  duplicate_rows: number
  failed_rows: number
  error_report_available: boolean
  message: string
}

export interface ImportJobItem {
  id: string
  filename: string
  bank_format: string
  status: string
  total_rows: number
  imported_rows: number
  duplicate_rows: number
  created_at: string
  completed_at?: string
  has_errors: boolean
}

export interface SMSParseResult {
  success: boolean
  bank_name?: string
  account_mask?: string
  amount_inr?: number
  transaction_type?: 'DEBIT' | 'CREDIT'
  merchant_name?: string
  clean_narration?: string
  raw_narration?: string
  timestamp?: string
  available_balance_inr?: number
  upi_reference?: string
  parser_confidence: number
  parse_error?: string
  suggested_category_slug?: string
  category_id?: string
  category_name?: string
  category_color?: string
  categorization_method?: string
  categorization_confidence?: number
}

export interface RecurringPattern {
  merchant: string
  cadence: string
  occurrences: number
  avg_amount_inr: number
  min_amount_inr: number
  max_amount_inr: number
  amount_stability_pct: number
  last_date: string
  next_predicted_date?: string
  confidence_score: number
}

export interface DuplicateWarning {
  tx_id_1: string
  tx_id_2: string
  amount_inr: number
  merchant: string
  date_1: string
  date_2: string
  hours_apart: number
  warning: string
}

export interface SpendingAnomaly {
  transaction_id: string
  date: string
  amount_inr: number
  merchant?: string
  narration: string
  category: string
  category_q3_inr: number
  category_iqr_inr: number
  upper_bound_inr: number
  deviation_factor: number
  severity: 'MEDIUM' | 'HIGH'
}

export interface MerchantSummary {
  merchant_name: string
  total_spent_inr: number
  transaction_count: number
  average_ticket_inr: number
  first_transaction: string
  last_transaction: string
}

export interface ModelEvaluationData {
  evaluation_id?: string
  evaluated_at?: string
  version: string
  status?: string
  accuracy: number
  macro_f1: number
  train_size?: number
  test_size?: number
  classes: string[]
  classification_report?: Record<string, {
    precision: number
    recall: number
    'f1-score': number
    support: number
  }>
}

// ============================================================================
// Milestone 6: Planning, Health Score, Recommendations & Scenarios
// ============================================================================

export interface GoalSimulationResponse {
  goal_id: string
  target_amount_inr: number
  current_amount_inr: number
  simulated_monthly_contribution_inr: number
  required_monthly_inr: number
  target_date: string
  simulated_completion_date: string
  months_to_completion: number
  variance_months: number
  is_achievable: boolean
  feasibility_status: string
  message: string
}

export interface HealthFactorItem {
  factor_id: string
  name: string
  weight: number
  score: number
  max_score: number
  normalized_pct: number
  is_excluded: boolean
  exclusion_reason?: string
  metric_value?: string
  calculation_details: string
  actionable_tip: string
}

export interface HealthScoreResponse {
  overall_score: number
  grade: string
  disclaimer: string
  summary: string
  liquid_reserve_inr: number
  monthly_expenses_inr: number
  savings_rate_pct: number
  factors: HealthFactorItem[]
  excluded_factors_count: number
  top_improvement_actions: string[]
}

export interface RecommendationItem {
  id: string
  user_id: string
  recommendation_type: string
  title: string
  explanation: string
  data_period: string
  estimated_impact_inr: number
  impact_assumptions: string
  confidence: 'HIGH' | 'MEDIUM' | 'LOW'
  suggested_action: string
  action_type?: string
  action_payload_json?: string
  status: 'new' | 'accepted' | 'dismissed' | 'completed'
  created_at: string
  updated_at: string
}

export interface SimulationTrajectoryPoint {
  month_index: number
  month_label: string
  baseline_income_inr: number
  simulated_income_inr: number
  baseline_expense_inr: number
  simulated_expense_inr: number
  baseline_net_cashflow_inr: number
  simulated_net_cashflow_inr: number
  cumulative_baseline_balance_inr: number
  cumulative_simulated_balance_inr: number
  is_breached: boolean
  breach_gap_inr: number
}

export interface GoalImpactItem {
  goal_id: string
  goal_name: string
  original_completion_date: string
  simulated_completion_date: string
  variance_months: number
  status_change: string
}

export interface EnhancedSimulationParams {
  name?: string
  description?: string
  salary_delta_pct: number
  rent_delta_inr: number
  discretionary_reduction_pct: number
  new_recurring_monthly_inr: number
  unexpected_expense_inr: number
  monthly_savings_delta_inr: number
  horizon_months: number
}

export interface EnhancedSimulationResponse {
  baseline_monthly_income_inr: number
  simulated_monthly_income_inr: number
  baseline_monthly_expense_inr: number
  simulated_monthly_expense_inr: number
  baseline_monthly_savings_inr: number
  simulated_monthly_savings_inr: number
  net_monthly_differential_inr: number
  annual_savings_impact_inr: number
  emergency_reserve_floor_inr: number
  has_reserve_breach: boolean
  first_breach_month?: string
  min_projected_balance_inr: number
  goal_impacts: GoalImpactItem[]
  trajectory: SimulationTrajectoryPoint[]
}

export interface SavedScenarioItem {
  id: string
  user_id: string
  name: string
  description?: string
  params_json: string
  results_summary_json?: string
  created_at: string
  updated_at: string
}

export interface BudgetRecommendationItem {
  category_id: string
  category_name: string
  category_color?: string
  is_essential: boolean
  historical_avg_spent_inr: number
  suggested_budget_inr: number
  suggested_budget_paise: number
  current_budget_inr?: number
  variance_pct: number
  rationale: string
}

export interface BudgetRecommendationsResponse {
  month: number
  year: number
  total_suggested_inr: number
  recommendations: BudgetRecommendationItem[]
}

export interface CategoryReportItem {
  category_name: string
  category_color?: string
  spent_inr: number
  share_pct: number
  mom_change_inr: number
  mom_change_pct: number
}

export interface BudgetPerformanceReportItem {
  category_name: string
  budgeted_inr: number
  spent_inr: number
  variance_inr: number
  pacing_pct: number
  status: string
}

export interface MonthlyReportResponse {
  month: number
  year: number
  month_label: string
  total_income_inr: number
  total_expenses_inr: number
  net_savings_inr: number
  savings_rate_pct: number
  total_liquid_balance_inr: number
  accounts_count: number
  transactions_count: number
  category_breakdown: CategoryReportItem[]
  budget_performance: BudgetPerformanceReportItem[]
  total_budgeted_inr: number
  total_budget_spent_inr: number
  budget_utilization_pct: number
  forecast_month_end_balance_inr?: number
  actual_vs_forecast_delta_inr?: number
  anomalies_detected: string[]
  recommendation_summary: Record<string, number>
  generated_at: string
}

export interface NotificationItem {
  id: string
  user_id: string
  title: string
  message: string
  notification_type: string
  is_read: boolean
  action_url?: string
  created_at: string
}

