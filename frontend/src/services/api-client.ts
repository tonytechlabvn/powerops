// Typed fetch wrapper for PowerOps backend API with JWT auth + auto-refresh

import type { ApiError } from '../types/api-types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

// In-memory access token (not localStorage — XSS protection).
// Refresh token lives in the httpOnly `tb_refresh` cookie set by the backend.
let _accessToken: string | null = null
let _refreshPromise: Promise<boolean> | null = null

export function setAccessToken(token: string | null) {
  _accessToken = token
}

export function getAccessToken(): string | null {
  return _accessToken
}

class ApiClientError extends Error {
  status: number
  detail?: string

  constructor(error: ApiError) {
    super(error.message)
    this.name = 'ApiClientError'
    this.status = error.status
    this.detail = error.detail
  }
}

function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (_accessToken) {
    headers['Authorization'] = `Bearer ${_accessToken}`
  }
  return headers
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `HTTP ${res.status}: ${res.statusText}`
    let detail: string | undefined
    try {
      const body = await res.json()
      message = body.detail || body.message || message
      detail = body.detail
    } catch {
      // Response body not JSON
    }
    throw new ApiClientError({ message, status: res.status, detail })
  }
  const text = await res.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}

function buildUrl(path: string, params?: Record<string, string | undefined>): string {
  const url = new URL(`${BASE_URL}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined) url.searchParams.set(key, val)
    })
  }
  return url.toString()
}

// Attempt to refresh the access token using the httpOnly refresh cookie.
// Backend reads `tb_refresh` from cookies; no body needed.
async function attemptRefresh(): Promise<boolean> {
  try {
    const res = await fetch(`${BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
    })
    if (!res.ok) return false
    const data = await res.json()
    _accessToken = data.access_token
    return true
  } catch {
    return false
  }
}

// Deduplicated refresh — multiple 401s share the same refresh attempt
function refreshOnce(): Promise<boolean> {
  if (!_refreshPromise) {
    _refreshPromise = attemptRefresh().finally(() => {
      _refreshPromise = null
    })
  }
  return _refreshPromise
}

// Fetch with automatic 401 retry after silent refresh via cookie.
// Skips retry for the refresh endpoint itself to avoid recursion.
async function fetchWithRetry(url: string, init: RequestInit): Promise<Response> {
  const res = await fetch(url, init)
  if (res.status === 401 && !url.includes('/api/auth/refresh')) {
    const refreshed = await refreshOnce()
    if (refreshed) {
      const retryInit = { ...init, headers: authHeaders() }
      return fetch(url, retryInit)
    }
  }
  return res
}

export const apiClient = {
  async get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
    const res = await fetchWithRetry(buildUrl(path, params), {
      headers: authHeaders(),
      credentials: 'include',
    })
    return handleResponse<T>(res)
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetchWithRetry(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetchWithRetry(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: authHeaders(),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetchWithRetry(`${BASE_URL}${path}`, {
      method: 'PATCH',
      headers: authHeaders(),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  async del<T>(path: string): Promise<T> {
    const res = await fetchWithRetry(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: authHeaders(),
      credentials: 'include',
    })
    return handleResponse<T>(res)
  },
}

export { ApiClientError }
