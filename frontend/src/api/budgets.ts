import { apiClient } from './client'
import { Budget } from '@/types'

export async function getBudgetsApi(month?: number, year?: number): Promise<Budget[]> {
  const query = new URLSearchParams()
  if (month) query.set('month', month.toString())
  if (year) query.set('year', year.toString())
  return apiClient<Budget[]>(`/budgets?${query.toString()}`)
}

export async function createBudgetApi(data: {
  category_id: string
  month: number
  year: number
  amount_paise: number
  alert_threshold?: number
}): Promise<Budget> {
  return apiClient<Budget>('/budgets', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateBudgetApi(
  id: string,
  data: {
    amount_paise?: number
    alert_threshold?: number
  }
): Promise<Budget> {
  return apiClient<Budget>(`/budgets/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteBudgetApi(id: string): Promise<void> {
  return apiClient<void>(`/budgets/${id}`, {
    method: 'DELETE',
  })
}

export async function getBudgetRecommendationsApi(
  month?: number,
  year?: number
): Promise<import('@/types').BudgetRecommendationsResponse> {
  const query = new URLSearchParams()
  if (month) query.set('month', month.toString())
  if (year) query.set('year', year.toString())
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiClient<import('@/types').BudgetRecommendationsResponse>(`/budgets/recommendations${qs}`)
}

export async function applyBudgetRecommendationsApi(data: {
  month: number
  year: number
  selected_category_ids?: string[]
}): Promise<Budget[]> {
  return apiClient<Budget[]>('/budgets/apply-recommendations', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
