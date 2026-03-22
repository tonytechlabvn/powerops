// Auth context: Keycloak OIDC flow with PKCE
// Handles redirect to Keycloak, code exchange, token refresh, and logout

import { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import type { AuthUser } from '../../types/api-types'
import { apiClient, setAccessToken, setRefreshToken, getRefreshToken } from '../../services/api-client'

interface KeycloakConfig {
  url: string
  realm: string
  clientId: string
}

interface TokenResponse {
  access_token: string
  refresh_token: string
}

interface AuthContextValue {
  user: AuthUser | null
  isAuthenticated: boolean
  isLoading: boolean
  login: () => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

// PKCE helpers
function generateCodeVerifier(): string {
  const array = new Uint8Array(32)
  crypto.getRandomValues(array)
  return btoa(String.fromCharCode(...array))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

async function generateCodeChallenge(verifier: string): Promise<string> {
  const data = new TextEncoder().encode(verifier)
  const hash = await crypto.subtle.digest('SHA-256', data)
  return btoa(String.fromCharCode(...new Uint8Array(hash)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const navigate = useNavigate()
  const initRef = useRef(false)

  const fetchMe = useCallback(async (): Promise<AuthUser> => {
    const me = await apiClient.get<AuthUser>('/api/auth/me')
    setUser(me)
    setIsAuthenticated(true)
    return me
  }, [])

  // Redirect to Keycloak login page
  const login = useCallback(async () => {
    try {
      const config = await apiClient.get<KeycloakConfig>('/api/auth/keycloak-config')
      const verifier = generateCodeVerifier()
      const challenge = await generateCodeChallenge(verifier)

      // Store verifier for code exchange
      sessionStorage.setItem('pkce_verifier', verifier)

      const redirectUri = `${window.location.origin}/auth/callback`
      const authUrl = `${config.url}/realms/${config.realm}/protocol/openid-connect/auth`
        + `?client_id=${config.clientId}`
        + `&response_type=code`
        + `&scope=openid email profile`
        + `&redirect_uri=${encodeURIComponent(redirectUri)}`
        + `&code_challenge=${challenge}`
        + `&code_challenge_method=S256`

      window.location.href = authUrl
    } catch (err) {
      console.error('Failed to initiate Keycloak login:', err)
    }
  }, [])

  // Exchange auth code for tokens
  const handleCallback = useCallback(async (code: string) => {
    const redirectUri = `${window.location.origin}/auth/callback`
    const codeVerifier = sessionStorage.getItem('pkce_verifier')
    sessionStorage.removeItem('pkce_verifier')
    try {
      const data = await apiClient.post<TokenResponse>('/api/auth/callback', {
        code,
        redirect_uri: redirectUri,
        code_verifier: codeVerifier,
      })
      setAccessToken(data.access_token)
      setRefreshToken(data.refresh_token || null)
      await fetchMe()
      navigate('/', { replace: true })
    } catch (err) {
      console.error('Token exchange failed:', err)
      navigate('/login', { replace: true })
    }
  }, [fetchMe, navigate])

  // Refresh access token using refresh token
  const refreshTokens = useCallback(async (): Promise<boolean> => {
    const currentRefresh = getRefreshToken()
    if (!currentRefresh) return false
    try {
      const data = await apiClient.post<TokenResponse>('/api/auth/refresh', {
        refresh_token: currentRefresh,
      })
      setAccessToken(data.access_token)
      setRefreshToken(data.refresh_token || currentRefresh)
      return true
    } catch {
      return false
    }
  }, [])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post('/api/auth/logout', {
        refresh_token: getRefreshToken(),
      })
    } catch {
      // Best-effort logout
    } finally {
      setAccessToken(null)
      setRefreshToken(null)
      setUser(null)
      setIsAuthenticated(false)
      sessionStorage.removeItem('pkce_verifier')
      navigate('/login')
    }
  }, [navigate])

  // On mount: check for auth code in URL or try token refresh
  useEffect(() => {
    if (initRef.current) return
    initRef.current = true

    async function init() {
      // Check for Keycloak callback code in URL
      const params = new URLSearchParams(window.location.search)
      const code = params.get('code')

      if (code && window.location.pathname === '/auth/callback') {
        await handleCallback(code)
        setIsLoading(false)
        return
      }

      // Try refreshing existing session
      const refreshed = await refreshTokens()
      if (refreshed) {
        try {
          await fetchMe()
        } catch {
          setAccessToken(null)
          setRefreshToken(null)
          setIsAuthenticated(false)
        }
      }
      setIsLoading(false)
    }

    init()
  }, [handleCallback, refreshTokens, fetchMe])

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
