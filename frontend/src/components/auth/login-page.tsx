// Login page: redirects to Keycloak for authentication
// Shows a branded splash screen with "Sign in" button that triggers OIDC flow

import { useAuth } from './auth-provider'

export function LoginPage() {
  const { login, isLoading } = useAuth()

  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        {/* Logo / heading */}
        <div className="text-center mb-8">
          <h1 className="text-2xl font-semibold text-zinc-100">PowerOps</h1>
          <p className="text-zinc-500 text-sm mt-1">AI-powered Terraform automation</p>
        </div>

        {/* Card */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
          <p className="text-zinc-400 text-sm text-center mb-4">
            Sign in with your organization account
          </p>

          <button
            onClick={() => login()}
            disabled={isLoading}
            className="w-full bg-blue-500 hover:bg-blue-600 disabled:bg-blue-500/50 disabled:cursor-not-allowed text-white font-medium rounded px-4 py-2 text-sm transition-colors"
          >
            {isLoading ? 'Loading...' : 'Sign in with Keycloak'}
          </button>
        </div>

        <p className="text-center text-zinc-600 text-xs mt-4">
          Authentication managed by Keycloak SSO
        </p>
      </div>
    </div>
  )
}
