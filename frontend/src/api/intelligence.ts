import { apiClient } from './client'
import {
  RecurringPattern,
  DuplicateWarning,
  SpendingAnomaly,
  MerchantSummary,
  ModelEvaluationData,
} from '@/types'

export async function getRecurringCommitmentsApi(
  lookbackDays: number = 180
): Promise<RecurringPattern[]> {
  return apiClient<RecurringPattern[]>(
    `/intelligence/recurring?lookback_days=${lookbackDays}`
  )
}

export async function getDuplicateWarningsApi(): Promise<DuplicateWarning[]> {
  return apiClient<DuplicateWarning[]>('/intelligence/duplicates')
}

export async function getSpendingAnomaliesApi(
  lookbackDays: number = 90,
  iqrMultiplier: number = 1.75
): Promise<SpendingAnomaly[]> {
  return apiClient<SpendingAnomaly[]>(
    `/intelligence/anomalies?lookback_days=${lookbackDays}&iqr_multiplier=${iqrMultiplier}`
  )
}

export async function getMerchantSummariesApi(
  limit: number = 15
): Promise<MerchantSummary[]> {
  return apiClient<MerchantSummary[]>(`/intelligence/merchants?limit=${limit}`)
}

export async function getModelEvaluationApi(): Promise<ModelEvaluationData> {
  return apiClient<ModelEvaluationData>('/intelligence/model-evaluation')
}

export async function retrainModelApi(): Promise<{
  status: string
  version: string
  metrics: any
}> {
  return apiClient<{ status: string; version: string; metrics: any }>(
    '/intelligence/retrain-model',
    {
      method: 'POST',
    }
  )
}
