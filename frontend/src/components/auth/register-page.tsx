// Register page: Redirect to Keycloak for signup
// Phase 0 Keycloak auth: self-service registration via Keycloak realm

import { useEffect } from 'react'
import { useAuth } from './auth-provider'

export function RegisterPage() {
  const { login } = useAuth()

  useEffect(() => {
    // Immediately redirect to Keycloak login (handles signup via realm registration)
    login()
  }, [login])

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center">
          <h1 className="text-2xl font-semibold text-zinc-100">PowerOps</h1>
          <p className="text-zinc-400 text-sm mt-4">Redirecting to Keycloak...</p>
        </div>
      </div>
    </div>
  )
}
