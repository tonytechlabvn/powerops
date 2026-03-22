// Keycloak OIDC callback handler — shows loading while code exchange happens
// The actual exchange is handled by AuthProvider; this is just the visual placeholder

export function AuthCallbackPage() {
  return (
    <div className="min-h-screen bg-zinc-950 flex items-center justify-center px-4">
      <div className="text-center">
        <h1 className="text-xl font-semibold text-zinc-100 mb-2">PowerOps</h1>
        <p className="text-zinc-400 text-sm">Completing sign in...</p>
      </div>
    </div>
  )
}
