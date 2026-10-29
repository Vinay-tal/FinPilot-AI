import { apiClient } from './client'
import { FinancialInsight } from '@/types'

export async function getInsightsApi(is_resolved?: boolean): Promise<FinancialInsight[]> {
  const query = new URLSearchParams()
  if (is_resolved !== undefined) {
    query.set('is_resolved', is_resolved.toString())
  }
  return apiClient<FinancialInsight[]>(`/insights?${query.toString()}`)
}

export async function resolveInsightApi(id: string): Promise<FinancialInsight> {
  return apiClient<FinancialInsight>(`/insights/${id}/resolve`, {
    method: 'POST',
  })
}
