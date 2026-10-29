import { apiClient } from './client'
import { SavingsGoal } from '@/types'

export async function getGoalsApi(): Promise<SavingsGoal[]> {
  return apiClient<SavingsGoal[]>('/goals')
}

export async function createGoalApi(data: {
  name: string
  target_amount_paise: number
  current_amount_paise?: number
  target_date: string
  category?: string
  priority?: string
}): Promise<SavingsGoal> {
  return apiClient<SavingsGoal>('/goals', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateGoalApi(
  id: string,
  data: {
    current_amount_paise?: number
    target_amount_paise?: number
    monthly_contribution_paise?: number
    name?: string
    status?: string
    priority?: string
  }
): Promise<SavingsGoal> {
  return apiClient<SavingsGoal>(`/goals/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteGoalApi(id: string): Promise<void> {
  return apiClient<void>(`/goals/${id}`, {
    method: 'DELETE',
  })
}

export async function simulateGoalApi(
  id: string,
  monthly_contribution_inr: number
): Promise<import('@/types').GoalSimulationResponse> {
  return apiClient<import('@/types').GoalSimulationResponse>(`/goals/${id}/simulate`, {
    method: 'POST',
    body: JSON.stringify({ monthly_contribution_inr }),
  })
}
