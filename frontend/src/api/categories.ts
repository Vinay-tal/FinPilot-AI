import { apiClient } from './client'
import { TransactionCategory } from '@/types'

export async function getCategoriesApi(): Promise<TransactionCategory[]> {
  return apiClient<TransactionCategory[]>('/categories')
}

export async function createCategoryApi(data: {
  name: string
  slug: string
  icon?: string
  color?: string
  is_income?: boolean
}): Promise<TransactionCategory> {
  return apiClient<TransactionCategory>('/categories', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
