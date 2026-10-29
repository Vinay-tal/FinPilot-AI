import { apiClient } from './client'
import { Transaction, PaginatedResponse } from '@/types'

export interface TransactionFilterParams {
  page?: number
  limit?: number
  account_id?: string
  category_id?: string
  start_date?: string
  end_date?: string
  type?: string
  search?: string
  sort_by?: string
  sort_order?: string
}

export async function getTransactionsApi(params: TransactionFilterParams = {}): Promise<PaginatedResponse<Transaction>> {
  const query = new URLSearchParams()
  if (params.page) query.set('page', params.page.toString())
  if (params.limit) query.set('limit', params.limit.toString())
  if (params.account_id) query.set('account_id', params.account_id)
  if (params.category_id) query.set('category_id', params.category_id)
  if (params.start_date) query.set('start_date', params.start_date)
  if (params.end_date) query.set('end_date', params.end_date)
  if (params.type) query.set('type', params.type)
  if (params.search) query.set('search', params.search)
  if (params.sort_by) query.set('sort_by', params.sort_by)
  if (params.sort_order) query.set('sort_order', params.sort_order)

  return apiClient<PaginatedResponse<Transaction>>(`/transactions?${query.toString()}`)
}

export async function createTransactionApi(data: {
  account_id: string
  category_id: string
  date: string
  amount_paise: number
  transaction_type: 'DEBIT' | 'CREDIT'
  narration: string
  merchant_name?: string
  payment_mode?: string
  reference_id?: string
}): Promise<Transaction> {
  return apiClient<Transaction>('/transactions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteTransactionApi(id: string): Promise<void> {
  return apiClient<void>(`/transactions/${id}`, {
    method: 'DELETE',
  })
}

export async function reclassifyTransactionApi(
  id: string,
  categoryId: string
): Promise<Transaction> {
  return apiClient<Transaction>(`/transactions/${id}/reclassify`, {
    method: 'PATCH',
    body: JSON.stringify({ category_id: categoryId }),
  })
}
