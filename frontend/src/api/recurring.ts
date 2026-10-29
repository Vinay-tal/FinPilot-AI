import { apiClient } from './client'
import { RecurringTransaction } from '@/types'

export async function getRecurringApi(): Promise<RecurringTransaction[]> {
  return apiClient<RecurringTransaction[]>('/recurring')
}

export async function createRecurringApi(data: {
  category_id: string
  name: string
  merchant_name: string
  expected_amount_paise: number
  frequency?: string
  next_expected_date: string
}): Promise<RecurringTransaction> {
  return apiClient<RecurringTransaction>('/recurring', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteRecurringApi(id: string): Promise<void> {
  return apiClient<void>(`/recurring/${id}`, {
    method: 'DELETE',
  })
}
