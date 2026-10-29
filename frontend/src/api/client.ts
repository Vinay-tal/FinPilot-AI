const BASE_URL = '/api/v1'

export class ApiError extends Error {
  statusCode: number
  errorCode: string
  details?: Record<string, unknown>

  constructor(message: string, statusCode: number, errorCode: string = 'API_ERROR', details?: Record<string, unknown>) {
    super(message)
    this.name = 'ApiError'
    this.statusCode = statusCode
    this.errorCode = errorCode
    this.details = details
  }
}

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('finpilot_token')

  const headers: Record<string, string> = {
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint.startsWith('/') ? '' : '/'}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (response.status === 204) {
    return {} as T
  }

  let data
  try {
    data = await response.json()
  } catch {
    data = null
  }

  if (!response.ok) {
    if (response.status === 401) {
      // Auto-clear invalid token on auth errors
      localStorage.removeItem('finpilot_token')
      localStorage.removeItem('finpilot_user')
    }

    const message = data?.message || data?.detail || 'An unexpected error occurred.'
    const errorCode = data?.error_code || 'HTTP_ERROR'
    const details = data?.details
    throw new ApiError(message, response.status, errorCode, details)
  }

  return data as T
}
