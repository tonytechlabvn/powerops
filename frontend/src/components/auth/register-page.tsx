// Register page — uses design-system primitives. Matches login-page styling.

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from './auth-provider'
import { apiClient } from '../../services/api-client'
import { Button } from '../_design-system/button'
import { Card, CardBody } from '../_design-system/card'
import { Input } from '../_design-system/input'

export function RegisterPage() {
  const { login } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [orgName, setOrgName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError(null)
    setIsSubmitting(true)

    try {
      await apiClient.post('/api/auth/register', {
        name, email, password,
        ...(orgName.trim() ? { org_name: orgName.trim() } : {}),
      })
      await login(email, password)
      navigate('/')
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registration failed'
      setError(msg)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="relative min-h-screen bg-zinc-950 flex items-center justify-center px-4 overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(59,130,246,0.10),_transparent_50%)]" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,_rgba(255,255,255,0.02)_1px,_transparent_1px),_linear-gradient(to_bottom,_rgba(255,255,255,0.02)_1px,_transparent_1px)] bg-[size:24px_24px]" />

      <div className="relative w-full max-w-sm">
        <div className="flex flex-col items-center mb-8">
          <div className="h-10 w-10 rounded-lg bg-blue-500 flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-blue-500/20">
            P
          </div>
          <h1 className="mt-3 text-xl font-semibold text-zinc-100 tracking-tight">PowerOps</h1>
          <p className="text-zinc-500 text-sm mt-1">Create your account</p>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div role="alert" className="rounded-md bg-red-500/10 border border-red-500/20 text-red-400 text-xs px-3 py-2">
                  {error}
                </div>
              )}

              <div>
                <label htmlFor="name" className="block text-xs font-medium text-zinc-400 mb-1.5">Name</label>
                <Input
                  id="name" type="text" required autoComplete="name"
                  value={name} onChange={e => setName(e.target.value)}
                  placeholder="Jane Smith"
                />
              </div>

              <div>
                <label htmlFor="email" className="block text-xs font-medium text-zinc-400 mb-1.5">Email</label>
                <Input
                  id="email" type="email" required autoComplete="email"
                  value={email} onChange={e => setEmail(e.target.value)}
                  placeholder="you@example.com"
                />
              </div>

              <div>
                <label htmlFor="password" className="block text-xs font-medium text-zinc-400 mb-1.5">Password</label>
                <Input
                  id="password" type="password" required autoComplete="new-password"
                  value={password} onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                />
              </div>

              <div>
                <label htmlFor="org-name" className="block text-xs font-medium text-zinc-400 mb-1.5">
                  Organization <span className="text-zinc-600 font-normal">(optional)</span>
                </label>
                <Input
                  id="org-name" type="text" autoComplete="organization"
                  value={orgName} onChange={e => setOrgName(e.target.value)}
                  placeholder="Acme Corp"
                />
              </div>

              <Button type="submit" disabled={isSubmitting} className="w-full">
                {isSubmitting ? 'Creating account…' : 'Create account'}
              </Button>
            </form>
          </CardBody>
        </Card>

        <p className="text-center text-zinc-500 text-xs mt-4">
          Already have an account?{' '}
          <Link to="/login" className="text-blue-400 hover:text-blue-300 transition-colors">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
