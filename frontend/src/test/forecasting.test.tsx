import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ForecastingPage } from '@/pages/ForecastingPage'
import { ToastProvider } from '@/context/ToastContext'
import * as forecastingApi from '@/api/forecasting'
import {
  ForecastResponse,
  CategoryForecastItem,
  ForecastEvaluationResponse,
  StressScenarioResponse,
} from '@/types'

vi.mock('@/api/forecasting')

const mockForecastResponse: ForecastResponse = {
  model_version: 'v1.4.0-ridge-calendar',
  horizon_days: 30,
  current_balance_inr: 85000,
  projected_end_balance_inr: 72400,
  net_projected_change_inr: -12600,
  daily_burn_rate_inr: -420,
  shortfall_detected: false,
  shortfall_date: undefined,
  min_projected_balance_inr: 65200,
  risk_analysis: {
    shortfall_detected: false,
    shortfall_date: null,
    min_projected_balance_inr: 65200,
    risk_level: 'SAFE',
    shortfall_probability_pct: 8,
    probability_calibrated: true,
    days_until_shortfall: null,
    buffer_deficit_inr: 0,
    reserve_threshold_inr: 10000,
  },
  explanation: {
    summary_narrative: 'Balance projected to decline moderately before rebounding post-salary.',
    observed_facts: [
      'Current liquid balance: ₹85,000.00 across active accounts',
      'Average daily historical discretionary spend: ₹420.00',
    ],
    assumptions: [
      'Scheduled recurring salary credit of ₹1,20,000.00 on 2026-10-31',
      'Scheduled recurring rent payment of ₹25,000.00 on 2026-11-01',
    ],
    positive_drivers: [
      {
        factor: 'Salary Credit',
        impact_inr: 120000,
        description: 'Expected salary credit (+₹1,20,000.00)',
      },
    ],
    negative_drivers: [
      {
        factor: 'Rent Outflow',
        impact_inr: 25000,
        description: 'Upcoming rent & utilities (-₹25,000.00)',
      },
    ],
  },
  historical_points: [
    { date: '2026-10-21', display_date: '21 Oct', balance_inr: 86500, is_historical: true },
    { date: '2026-10-22', display_date: '22 Oct', balance_inr: 85000, is_historical: true },
  ],
  forecast_points: [
    {
      date: '2026-10-24',
      display_date: '24 Oct',
      balance_inr: 84500,
      lower_bound_inr: 82500,
      upper_bound_inr: 86500,
      lower_bound_95_inr: 80500,
      upper_bound_95_inr: 88500,
    },
  ],
}

const mockCategories: CategoryForecastItem[] = [
  {
    category_id: 'cat-food',
    category_name: 'Food & Dining',
    category_slug: 'food-dining',
    category_color: '#F97316',
    current_spent_inr: 12400,
    daily_run_rate_inr: 550,
    projected_remaining_inr: 4100,
    projected_month_end_inr: 16500,
    pacing_ratio: 0.916,
    historical_90d_total_inr: 45000,
    pacing_status: 'ON_TRACK',
  },
  {
    category_id: 'cat-groceries',
    category_name: 'Groceries',
    category_slug: 'groceries',
    category_color: '#10B981',
    current_spent_inr: 10200,
    daily_run_rate_inr: 400,
    projected_remaining_inr: 3300,
    projected_month_end_inr: 13500,
    pacing_ratio: 1.125,
    historical_90d_total_inr: 32000,
    pacing_status: 'ELEVATED',
  },
]

const mockEvaluation: ForecastEvaluationResponse = {
  status: 'SUCCESS',
  model_version: 'v1.4.0-ridge-calendar',
  evaluated_at: '2026-10-23T02:00:00Z',
  data_coverage_days: 90,
  walk_forward_splits: 3,
  test_window_days: 14,
  baseline: {
    name: 'Burn-Rate Baseline + DOW',
    mae_inr: 3200.5,
    rmse_inr: 4100.2,
  },
  advanced_model: {
    name: 'Ridge ML Regressor (Calendar & Momentum)',
    mae_inr: 2450.8,
    rmse_inr: 3120.4,
  },
  improvement_pct: 23.4,
  recommended_model: 'Ridge ML Regressor (Calendar & Momentum)',
}

const mockScenarioResponse: StressScenarioResponse = {
  scenario_type: 'SALARY_DELAY',
  shock_description: '7-day delay in expected primary salary credit',
  horizon_days: 30,
  baseline_end_balance_inr: 72400,
  stressed_end_balance_inr: 72400,
  delta_end_balance_inr: 0,
  baseline_min_balance_inr: 65200,
  stressed_min_balance_inr: 45200,
  shortfall_induced: false,
  stressed_shortfall_date: null,
  stressed_probability_pct: 12,
  stressed_risk_level: 'LOW',
  comparison_points: [
    {
      date: '2026-10-31',
      display_date: '31 Oct',
      baseline_balance_inr: 175000,
      stressed_balance_inr: 55000,
      event_name: 'Delayed Salary Credit',
    },
  ],
}

function renderForecastingPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <ForecastingPage />
      </ToastProvider>
    </QueryClientProvider>
  )
}

describe('Forecasting & Risk Engine UI Suite', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(forecastingApi.getForecastApi).mockResolvedValue(mockForecastResponse)
    vi.mocked(forecastingApi.getCategoryForecastsApi).mockResolvedValue(mockCategories)
    vi.mocked(forecastingApi.getForecastEvaluationApi).mockResolvedValue(mockEvaluation)
    vi.mocked(forecastingApi.generateAndSaveForecastApi).mockResolvedValue(mockForecastResponse)
    vi.mocked(forecastingApi.simulateStressScenarioApi).mockResolvedValue(mockScenarioResponse)
  })

  it('renders forecasting header and KPI summary cards', async () => {
    renderForecastingPage()

    // Header
    expect(
      screen.getByText('Financial Forecasting & Risk Analysis Engine')
    ).toBeInTheDocument()

    // Wait for data load
    await waitFor(() => {
      expect(screen.getByText('Current Verified Balance')).toBeInTheDocument()
    })

    expect(screen.getByText('₹85,000.00')).toBeInTheDocument()
    expect(screen.getByText('Projected 30-Day Balance')).toBeInTheDocument()
    expect(screen.getByText('₹72,400.00')).toBeInTheDocument()
    expect(screen.getByText('Minimum Dip Point')).toBeInTheDocument()
    expect(screen.getByText('₹65,200.00')).toBeInTheDocument()
    expect(screen.getByText('Shortfall Risk Probability')).toBeInTheDocument()
    expect(screen.getByText('8%')).toBeInTheDocument()
  })

  it('displays tabs and switches to Explainability & Drivers tab', async () => {
    renderForecastingPage()

    await waitFor(() => {
      expect(screen.getByText('Current Verified Balance')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText('Explainability & Drivers'))

    await waitFor(() => {
      expect(
        screen.getByText('Forecast Explainability & Factor Attribution')
      ).toBeInTheDocument()
      expect(screen.getByText('Observed Facts (Empirical Data)')).toBeInTheDocument()
      expect(
        screen.getByText(/Current liquid balance: ₹85,000.00/)
      ).toBeInTheDocument()
      expect(screen.getByText('Modeling Assumptions')).toBeInTheDocument()
      expect(
        screen.getByText(/Scheduled recurring salary credit/)
      ).toBeInTheDocument()
    })
  })

  it('renders Category Projections tab with Empirical Bayes forecast', async () => {
    renderForecastingPage()

    await waitFor(() => {
      expect(screen.getByText('Current Verified Balance')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText(/Category-Level Projections/))

    await waitFor(() => {
      expect(screen.getByText('Food & Dining')).toBeInTheDocument()
      expect(screen.getByText('Groceries')).toBeInTheDocument()
      expect(screen.getByText('₹16,500.00')).toBeInTheDocument()
      expect(screen.getByText('₹13,500.00')).toBeInTheDocument()
    })
  })

  it('renders Walk-Forward CV Benchmark tab with MAE and RMSE improvements', async () => {
    renderForecastingPage()

    await waitFor(() => {
      expect(screen.getByText('Current Verified Balance')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText(/Model Benchmark & Temporal CV/))

    await waitFor(() => {
      expect(
        screen.getByText('Walk-Forward Temporal Cross-Validation')
      ).toBeInTheDocument()
      expect(screen.getByText('+23.4% error delta vs baseline')).toBeInTheDocument()
      expect(screen.getByText('MAE: ₹2,450.80')).toBeInTheDocument()
      expect(screen.getByText('MAE: ₹3,200.50')).toBeInTheDocument()
    })
  })

  it('simulates stress scenario on the Stress Scenario Simulator tab', async () => {
    renderForecastingPage()

    await waitFor(() => {
      expect(screen.getByText('Current Verified Balance')).toBeInTheDocument()
    })

    fireEvent.click(screen.getByText(/Stress-Test Simulator/))

    await waitFor(() => {
      expect(
        screen.getByText('Synthetic Stress-Test Scenario Simulator')
      ).toBeInTheDocument()
    })

    // Click Re-simulate Shock
    const runBtn = screen.getByText('Re-simulate Shock')
    fireEvent.click(runBtn)

    await waitFor(() => {
      expect(forecastingApi.simulateStressScenarioApi).toHaveBeenCalled()
      expect(
        screen.getByText(/7-day delay in expected primary salary credit/)
      ).toBeInTheDocument()
    })
  })
})
