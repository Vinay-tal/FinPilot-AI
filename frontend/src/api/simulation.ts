import { apiClient } from './client'
import {
  EnhancedSimulationParams,
  EnhancedSimulationResponse,
  SavedScenarioItem,
} from '@/types'

// Legacy interface for compatibility
export interface SimulationParams {
  income_delta_pct: number
  rent_delta_inr: number
  discretionary_reduction_pct: number
  new_recurring_monthly_inr: number
  lump_sum_inr: number
  monthly_savings_delta_inr?: number
  horizon_months?: number
}

export async function runSimulationApi(params: SimulationParams | EnhancedSimulationParams): Promise<any> {
  // Normalize params for backend
  const payload = {
    salary_delta_pct: (params as any).salary_delta_pct ?? (params as any).income_delta_pct ?? 0,
    rent_delta_inr: params.rent_delta_inr || 0,
    discretionary_reduction_pct: params.discretionary_reduction_pct || 0,
    new_recurring_monthly_inr: params.new_recurring_monthly_inr || 0,
    unexpected_expense_inr: (params as any).unexpected_expense_inr ?? (params as any).lump_sum_inr ?? 0,
    monthly_savings_delta_inr: params.monthly_savings_delta_inr || 0,
    horizon_months: params.horizon_months || 12,
  }

  return apiClient<EnhancedSimulationResponse>('/simulation/run', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function listSavedScenariosApi(): Promise<SavedScenarioItem[]> {
  return apiClient<SavedScenarioItem[]>('/simulation/scenarios')
}

export async function saveScenarioApi(
  name: string,
  description?: string,
  parameters?: EnhancedSimulationParams
): Promise<SavedScenarioItem> {
  return apiClient<SavedScenarioItem>('/simulation/scenarios', {
    method: 'POST',
    body: JSON.stringify({
      name,
      description,
      parameters,
    }),
  })
}

export async function deleteSavedScenarioApi(id: string): Promise<void> {
  return apiClient<void>(`/simulation/scenarios/${id}`, {
    method: 'DELETE',
  })
}
