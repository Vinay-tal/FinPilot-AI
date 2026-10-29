import { apiClient } from './client'

export interface SystemReadiness {
  status: string
  database: string
  database_url_masked: string
  ai_provider: string
  diagnostics: Record<string, any>
}

export interface SystemHealth {
  status: string
  version: string
  service: string
}

export async function getSystemReadinessApi(): Promise<SystemReadiness> {
  return apiClient<SystemReadiness>('/ready')
}

export async function getSystemHealthApi(): Promise<SystemHealth> {
  return apiClient<SystemHealth>('/health')
}
