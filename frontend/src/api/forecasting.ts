import { apiClient } from './client'
import {
  ForecastResponse,
  CategoryForecastItem,
  ForecastEvaluationResponse,
  StressScenarioResponse,
} from '@/types'

export interface ForecastRequestParams {
  days?: number
  model_type?: 'auto' | 'baseline' | 'ridge' | 'holt_winters'
  reserve_threshold_inr?: number
}

export async function getForecastApi(
  params: ForecastRequestParams = {}
): Promise<ForecastResponse> {
  const query = new URLSearchParams()
  if (params.days) query.set('days', params.days.toString())
  if (params.model_type) query.set('model_type', params.model_type)
  if (params.reserve_threshold_inr)
    query.set('reserve_threshold_inr', params.reserve_threshold_inr.toString())

  return apiClient<ForecastResponse>(`/forecasting?${query.toString()}`)
}

export async function generateAndSaveForecastApi(
  params: ForecastRequestParams = {}
): Promise<ForecastResponse> {
  const query = new URLSearchParams()
  if (params.days) query.set('days', params.days.toString())
  if (params.model_type) query.set('model_type', params.model_type)
  if (params.reserve_threshold_inr)
    query.set('reserve_threshold_inr', params.reserve_threshold_inr.toString())

  return apiClient<ForecastResponse>(`/forecasting/generate?${query.toString()}`, {
    method: 'POST',
  })
}

export async function getLatestForecastApi(): Promise<any> {
  return apiClient<any>('/forecasting/latest')
}

export async function getCategoryForecastsApi(): Promise<CategoryForecastItem[]> {
  return apiClient<CategoryForecastItem[]>('/forecasting/categories')
}

export async function getForecastEvaluationApi(): Promise<ForecastEvaluationResponse> {
  return apiClient<ForecastEvaluationResponse>('/forecasting/evaluation')
}

export async function simulateStressScenarioApi(data: {
  scenario_type: 'SALARY_DELAY' | 'EMERGENCY_EXPENSE' | 'SPENDING_SURGE'
  horizon_days?: number
  delay_days?: number
  expense_amount_inr?: number
  spend_surge_pct?: number
}): Promise<StressScenarioResponse> {
  return apiClient<StressScenarioResponse>('/forecasting/scenarios', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
