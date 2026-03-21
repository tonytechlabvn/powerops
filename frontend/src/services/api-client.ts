// Typed fetch wrapper for PowerOps backend API with JWT auth support

import type { ApiError } from '../types/api-types'

const BASE_URL = import.meta.env.VITE_API_URL || ''

// In-memory token store (not localStorage — XSS protection)
let _accessToken: string | null = null

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

export const apiClient = {
  async get<T>(path: string, params?: Record<string, string | undefined>): Promise<T> {
    const res = await fetch(buildUrl(path, params), {
      headers: authHeaders(),
      credentials: 'include',
    })
    return handleResponse<T>(res)
  },

  async post<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'POST',
      headers: authHeaders(),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  async put<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'PUT',
      headers: authHeaders(),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  async patch<T>(path: string, body?: unknown): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'PATCH',
      headers: authHeaders(),
      credentials: 'include',
      body: body !== undefined ? JSON.stringify(body) : undefined,
    })
    return handleResponse<T>(res)
  },

  async del<T>(path: string): Promise<T> {
    const res = await fetch(`${BASE_URL}${path}`, {
      method: 'DELETE',
      headers: authHeaders(),
      credentials: 'include',
    })
    return handleResponse<T>(res)
  },
}

export { ApiClientError }
