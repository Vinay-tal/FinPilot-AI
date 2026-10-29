import { apiClient } from './client'
import { FinancialAccount } from '@/types'

export async function getAccountsApi(): Promise<FinancialAccount[]> {
  return apiClient<FinancialAccount[]>('/accounts')
}

export async function createAccountApi(data: {
  name: string
  account_type: string
  institution: string
  account_number_mask?: string
  balance_paise?: number
  currency?: string
}): Promise<FinancialAccount> {
  return apiClient<FinancialAccount>('/accounts', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function deleteAccountApi(id: string): Promise<void> {
  return apiClient<void>(`/accounts/${id}`, {
    method: 'DELETE',
  })
}
