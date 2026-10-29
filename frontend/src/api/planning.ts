import { apiClient } from './client'
import {
  HealthScoreResponse,
  MonthlyReportResponse,
  NotificationItem,
} from '@/types'

export async function getHealthScoreApi(): Promise<HealthScoreResponse> {
  return apiClient<HealthScoreResponse>('/planning/health-score')
}

export async function getMonthlyReportApi(month?: number, year?: number): Promise<MonthlyReportResponse> {
  const query = new URLSearchParams()
  if (month) query.set('month', month.toString())
  if (year) query.set('year', year.toString())
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiClient<MonthlyReportResponse>(`/reports/monthly${qs}`)
}

export async function downloadReportCsvApi(month?: number, year?: number): Promise<void> {
  const query = new URLSearchParams()
  if (month) query.set('month', month.toString())
  if (year) query.set('year', year.toString())
  const qs = query.toString() ? `?${query.toString()}` : ''

  const token = localStorage.getItem('finpilot_token')
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`

  const resp = await fetch(`/api/v1/reports/export/csv${qs}`, { headers })
  const blob = await resp.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `FinPilot_Report_${month || 'current'}_${year || new Date().getFullYear()}.csv`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

export async function getNotificationsApi(): Promise<NotificationItem[]> {
  return apiClient<NotificationItem[]>('/notifications')
}

export async function markNotificationReadApi(id: string): Promise<NotificationItem> {
  return apiClient<NotificationItem>(`/notifications/${id}/read`, {
    method: 'POST',
  })
}

export async function markAllNotificationsReadApi(): Promise<void> {
  await apiClient<void>('/notifications/read-all', {
    method: 'POST',
  })
}
