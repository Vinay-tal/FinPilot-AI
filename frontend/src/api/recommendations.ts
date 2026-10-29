import { apiClient } from './client'
import { RecommendationItem } from '@/types'

export async function getRecommendationsApi(status?: string): Promise<RecommendationItem[]> {
  const query = new URLSearchParams()
  if (status && status !== 'all') {
    query.set('status', status)
  }
  const qs = query.toString() ? `?${query.toString()}` : ''
  return apiClient<RecommendationItem[]>(`/recommendations${qs}`)
}

export async function generateRecommendationsApi(): Promise<RecommendationItem[]> {
  return apiClient<RecommendationItem[]>('/recommendations/generate', {
    method: 'POST',
  })
}

export async function updateRecommendationStatusApi(
  id: string,
  status: 'new' | 'accepted' | 'dismissed' | 'completed'
): Promise<RecommendationItem> {
  return apiClient<RecommendationItem>(`/recommendations/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })
}

export async function applyRecommendationApi(id: string): Promise<{
  success: boolean
  message: string
  applied_action: string
  recommendation: RecommendationItem
}> {
  return apiClient<{
    success: boolean
    message: string
    applied_action: string
    recommendation: RecommendationItem
  }>(`/recommendations/${id}/apply`, {
    method: 'POST',
  })
}
