import { apiClient } from './client'
import { AuthResponse, User } from '@/types'

export async function loginApi(credentials: { email: string; password: string }): Promise<AuthResponse> {
  return apiClient<AuthResponse>('/auth/login', {
    method: 'POST',
    body: JSON.stringify(credentials),
  })
}

export async function registerApi(data: {
  email: string
  password: string
  full_name: string
  currency?: string
}): Promise<AuthResponse> {
  return apiClient<AuthResponse>('/auth/register', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function demoLoginApi(): Promise<AuthResponse> {
  return apiClient<AuthResponse>('/auth/demo-login', {
    method: 'POST',
  })
}

export async function getMeApi(): Promise<User> {
  return apiClient<User>('/auth/me')
}
