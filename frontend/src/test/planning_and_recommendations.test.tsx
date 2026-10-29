import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { FinancialHealthScoreView } from '@/components/insights/FinancialHealthScoreView'
import { PersonalizedRecommendationsView } from '@/components/insights/PersonalizedRecommendationsView'
import { GoalSimulationModal } from '@/components/goals/GoalSimulationModal'
import { SimulationPage } from '@/pages/SimulationPage'
import { ToastProvider } from '@/context/ToastContext'
import * as planningApi from '@/api/planning'
import * as recommendationsApi from '@/api/recommendations'
import * as goalsApi from '@/api/goals'
import * as simulationApi from '@/api/simulation'
import { HealthScoreResponse, RecommendationItem, SavingsGoal, EnhancedSimulationResponse } from '@/types'

vi.mock('@/api/planning')
vi.mock('@/api/recommendations')
vi.mock('@/api/goals')
vi.mock('@/api/simulation')

const mockHealthScore: HealthScoreResponse = {
  overall_score: 79,
  grade: 'Good',
  disclaimer: 'FinPilot AI Financial Health Score is an educational heuristic for personal planning, not a credit score.',
  summary: 'Solid overall financial baseline with strong savings rate.',
  liquid_reserve_inr: 120000,
  monthly_expenses_inr: 50000,
  savings_rate_pct: 32.5,
  excluded_factors_count: 1,
  factors: [
    {
      factor_id: 'savings_rate',
      name: 'Savings Rate',
      weight: 20,
      score: 16.4,
      max_score: 20,
      normalized_pct: 82,
      is_excluded: false,
      metric_value: '32.5%',
      calculation_details: 'Based on 32.5% savings rate against 20% benchmark',
      actionable_tip: 'Maintain automated transfers to maintain 30%+ savings.',
    },
    {
      factor_id: 'emergency_reserve',
      name: 'Emergency Reserve Coverage',
      weight: 20,
      score: 13.0,
      max_score: 20,
      normalized_pct: 65,
      is_excluded: false,
      metric_value: '3.1 months',
      calculation_details: 'Current reserves provide 3.1 months of survival runway',
      actionable_tip: 'Gradually build up to 6 months of emergency reserve.',
    },
    {
      factor_id: 'debt_burden',
      name: 'Debt Burden Ratio',
      weight: 15,
      score: 0,
      max_score: 15,
      normalized_pct: 0,
      is_excluded: true,
      exclusion_reason: 'No debt or EMI accounts reported in statements',
      calculation_details: 'Factor excluded and weight normalized proportionally',
      actionable_tip: 'Keep total debt payments under 30% if taking loans.',
    },
  ],
  top_improvement_actions: [
    'Increase monthly emergency fund allocation by ₹5,000 to reach 6-month safety buffer.',
    'Trim discretionary dining out to avoid category budget threshold alert.',
  ],
}

const mockRecommendations: RecommendationItem[] = [
  {
    id: 'rec-1',
    user_id: 'user-1',
    recommendation_type: 'BUDGET_OVERSPEND',
    title: 'Trim Dining Spending by ₹3,500',
    explanation: 'Dining out is currently pacing at 112% of historical baseline. Based on 42 verified UPI food transactions.',
    data_period: 'Last 30 Days (Oct 2026)',
    estimated_impact_inr: 3500,
    impact_assumptions: 'Assumes cutting 2 dining outings per month at ₹1,750 avg.',
    confidence: 'HIGH',
    suggested_action: 'Reduce Dining monthly budget limit from ₹18,000 to ₹14,500',
    action_type: 'SET_BUDGET',
    action_payload_json: JSON.stringify({ amount_inr: 14500 }),
    status: 'new',
    created_at: '2026-10-23T04:00:00Z',
    updated_at: '2026-10-23T04:00:00Z',
  },
  {
    id: 'rec-2',
    user_id: 'user-1',
    recommendation_type: 'RECURRING_REVIEW',
    title: 'Review Inactive Streaming Subscription',
    explanation: 'Streaming service billed ₹899/mo with no related service usage detected.',
    data_period: 'Last 60 Days',
    estimated_impact_inr: 899,
    impact_assumptions: 'Assumes cancellation saves ₹899 each month indefinitely.',
    confidence: 'MEDIUM',
    suggested_action: 'Cancel streaming subscription before next renewal',
    action_type: 'REVIEW_RECURRING',
    status: 'accepted',
    created_at: '2026-10-23T04:00:00Z',
    updated_at: '2026-10-23T04:00:00Z',
  },
]

const mockGoal: SavingsGoal = {
  id: 'goal-1',
  user_id: 'user-1',
  name: 'Emergency Fund',
  target_amount_paise: 30000000,
  target_amount_inr: 300000,
  current_amount_paise: 12000000,
  current_amount_inr: 120000,
  target_date: '2027-10-31',
  category: 'EMERGENCY_FUND',
  priority: 'HIGH',
  status: 'IN_PROGRESS',
  progress_pct: 40,
  monthly_contribution_inr: 15000,
  feasibility_status: 'ON_TRACK',
  required_monthly_inr: 15000,
  projected_completion_date: '2027-10-15',
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-10-23T00:00:00Z',
}

const mockSimulationResponse: EnhancedSimulationResponse = {
  baseline_monthly_income_inr: 120000,
  simulated_monthly_income_inr: 138000,
  baseline_monthly_expense_inr: 75000,
  simulated_monthly_expense_inr: 83000,
  baseline_monthly_savings_inr: 45000,
  simulated_monthly_savings_inr: 55000,
  net_monthly_differential_inr: 10000,
  annual_savings_impact_inr: 120000,
  emergency_reserve_floor_inr: 50000,
  has_reserve_breach: true,
  first_breach_month: 'Month 4',
  min_projected_balance_inr: 42000,
  goal_impacts: [
    {
      goal_id: 'goal-1',
      goal_name: 'Emergency Fund',
      original_completion_date: '2027-10-15',
      simulated_completion_date: '2027-07-10',
      variance_months: 3.2,
      status_change: 'ACCELERATED',
    },
  ],
  trajectory: [
    {
      month_index: 1,
      month_label: 'Nov 2026',
      baseline_income_inr: 120000,
      simulated_income_inr: 138000,
      baseline_expense_inr: 75000,
      simulated_expense_inr: 83000,
      baseline_net_cashflow_inr: 45000,
      simulated_net_cashflow_inr: 55000,
      cumulative_baseline_balance_inr: 145000,
      cumulative_simulated_balance_inr: 155000,
      is_breached: false,
      breach_gap_inr: 0,
    },
  ],
}

describe('Milestone 6: Financial Planning, Recommendations & Simulation', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    })
    vi.clearAllMocks()
  })

  it('renders Financial Health Score with educational disclaimer and factor calculations', async () => {
    vi.mocked(planningApi.getHealthScoreApi).mockResolvedValue(mockHealthScore)

    render(
      <QueryClientProvider client={queryClient}>
        <FinancialHealthScoreView />
      </QueryClientProvider>
    )

    // Check score and grade
    await waitFor(() => {
      expect(screen.getByText('79')).toBeInTheDocument()
    })
    expect(screen.getByText(/Good Foundation/i)).toBeInTheDocument()

    // Check educational disclaimer
    expect(
      screen.getByText(/educational heuristic for personal planning, not a credit score/i)
    ).toBeInTheDocument()

    // Check factors rendered
    expect(screen.getByText('Savings Rate')).toBeInTheDocument()
    expect(screen.getAllByText(/32.5%/i).length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText('Emergency Reserve Coverage')).toBeInTheDocument()
    expect(screen.getByText('3.1 months')).toBeInTheDocument()

    // Check excluded factors disclosed
    expect(screen.getByText(/Debt Burden Ratio/i)).toBeInTheDocument()

    // Check actionable tips
    expect(screen.getByText(/Increase monthly emergency fund allocation by ₹5,000/i)).toBeInTheDocument()
  })

  it('renders Personalized Recommendations with deduplication guarantee and lifecycle tabs', async () => {
    vi.mocked(recommendationsApi.getRecommendationsApi).mockResolvedValue(mockRecommendations)
    vi.mocked(recommendationsApi.updateRecommendationStatusApi).mockResolvedValue(mockRecommendations[0])

    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <PersonalizedRecommendationsView />
        </ToastProvider>
      </QueryClientProvider>
    )

    await waitFor(() => {
      expect(screen.getByText(/Trim Dining Spending by ₹3,500/i)).toBeInTheDocument()
    })

    // Verify deduplication guarantee text
    expect(screen.getByText(/deduplicated to prevent double-counting/i)).toBeInTheDocument()

    // Verify explanation and impact assumptions
    expect(screen.getByText(/Based on 42 verified UPI food transactions/i)).toBeInTheDocument()
    expect(screen.getByText(/Assumes cutting 2 dining outings/i)).toBeInTheDocument()
  })

  it('renders GoalSimulationModal and allows interactive timeline adjustments', async () => {
    vi.mocked(goalsApi.simulateGoalApi).mockResolvedValue({
      goal_id: 'goal-1',
      target_amount_inr: 300000,
      current_amount_inr: 120000,
      target_date: '2027-10-31',
      simulated_monthly_contribution_inr: 20000,
      required_monthly_inr: 15000,
      simulated_completion_date: '2027-07-20',
      months_to_completion: 9,
      variance_months: 3.3,
      is_achievable: true,
      feasibility_status: 'ON_TRACK',
      message: 'Goal will complete 3.3 months ahead of target date.',
    })

    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <GoalSimulationModal
            goal={mockGoal}
            isOpen={true}
            onClose={() => {}}
          />
        </ToastProvider>
      </QueryClientProvider>
    )

    expect(screen.getByText(/Goal Timeline Simulator/i)).toBeInTheDocument()
    expect(screen.getByText('Emergency Fund')).toBeInTheDocument()
    expect(screen.getByText(/Hypothetical Monthly Contribution/i)).toBeInTheDocument()
  })

  it('renders Scenario Simulator with reserve breach alert and multi-variable controls', async () => {
    vi.mocked(simulationApi.runSimulationApi).mockResolvedValue(mockSimulationResponse)
    vi.mocked(simulationApi.listSavedScenariosApi).mockResolvedValue([])

    render(
      <QueryClientProvider client={queryClient}>
        <ToastProvider>
          <SimulationPage />
        </ToastProvider>
      </QueryClientProvider>
    )

    // Check sliders present
    expect(screen.getByText('Salary Change')).toBeInTheDocument()
    expect(screen.getByText('Rent Adjustment (Monthly)')).toBeInTheDocument()
    expect(screen.getByText('Reduced Discretionary Spending')).toBeInTheDocument()
    expect(screen.getByText('New Monthly Subscriptions / EMI')).toBeInTheDocument()
    expect(screen.getByText('Unexpected Expense (Month 1)')).toBeInTheDocument()
    expect(screen.getByText('Monthly Savings Contribution Delta')).toBeInTheDocument()

    // Wait for simulation data to render
    await waitFor(() => {
      expect(screen.getByText(/Emergency Reserve Threshold Breach Warning/i)).toBeInTheDocument()
    })

    // Check goal impacts table
    expect(screen.getByText(/Savings Goal Completion Impacts/i)).toBeInTheDocument()
    expect(screen.getByText(/ACCELERATED/i)).toBeInTheDocument()
  })
})
