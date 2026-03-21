// Auth context: session recovery via httpOnly cookie refresh, login, logout
// Wraps the entire app to provide auth state to all children

import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AuthUser } from '../../types/api-types'
import { apiClient, setAccessToken } from '../../services/api-client'

interface LoginResponse {
  access_token: string
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()

  // Fetch current user profile and update state
  const fetchMe = useCallback(async (): Promise<AuthUser> => {
    const me = await apiClient.get<AuthUser>('/api/auth/me')
    setUser(me)
    setIsAuthenticated(true)
    return me
  }, [])

  // Attempt silent session recovery from httpOnly refresh cookie
  const refresh = useCallback(async (): Promise<void> => {
    try {
      const data = await apiClient.post<LoginResponse>('/api/auth/refresh')
      setAccessToken(data.access_token)
      await fetchMe()
    } catch {
      setAccessToken(null)
      setUser(null)
      setIsAuthenticated(false)
    }
  }, [fetchMe])

  // On mount: try to recover session via refresh token cookie
  useEffect(() => {
    refresh().finally(() => setIsLoading(false))
  }, [refresh])

  const login = useCallback(async (email: string, password: string): Promise<void> => {
    const data = await apiClient.post<LoginResponse>('/api/auth/login', { email, password })
    setAccessToken(data.access_token)
    await fetchMe()
  }, [fetchMe])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post('/api/auth/logout')
    } catch {
      // Best-effort logout — clear state regardless
    } finally {
      setAccessToken(null)
      setUser(null)
      setIsAuthenticated(false)
      navigate('/login')
    }
  }, [navigate])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  )
}
