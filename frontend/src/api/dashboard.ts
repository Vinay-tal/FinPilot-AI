import { apiClient } from './client'
import { DashboardSummary, CashflowTrendItem, CategorySpendItem } from '@/types'

export async function getDashboardSummaryApi(period: string = 'current_month'): Promise<DashboardSummary> {
  return apiClient<DashboardSummary>(`/dashboard/summary?period=${encodeURIComponent(period)}`)
}

export async function getCashflowTrendApi(months: number = 6): Promise<CashflowTrendItem[]> {
  return apiClient<CashflowTrendItem[]>(`/dashboard/cashflow-trend?months=${months}`)
}

export async function getCategoryBreakdownApi(period: string = 'current_month'): Promise<CategorySpendItem[]> {
  return apiClient<CategorySpendItem[]>(`/dashboard/category-breakdown?period=${encodeURIComponent(period)}`)
}

export const getCategorySpendingApi = getCategoryBreakdownApi

