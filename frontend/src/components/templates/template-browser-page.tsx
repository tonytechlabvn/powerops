// Template browser: grid with provider filter, and detail/deploy view

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Loader2, ChevronLeft } from 'lucide-react'
import { useTemplates, useTemplate } from '../../hooks/use-api'
import { TemplateCard } from './template-card'
import { TemplateDeployForm } from './template-deploy-form'
import { AutoDeployPanel } from './auto-deploy-panel'
import { Card, CardHeader, CardBody } from '../_design-system/card'
import { Badge } from '../_design-system/badge'
import { EmptyState } from '../_design-system/empty-state'
import { cn } from '../_design-system/lib/cn'

// --- Detail / deploy view for a single template ---
function TemplateDetailView({ name }: { name: string }) {
  const { data: template, isLoading, error } = useTemplate(name)

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-zinc-500 py-8">
        <Loader2 size={16} className="animate-spin" /> Loading template…
      </div>
    )
  }
  if (error || !template) {
    return (
      <div className="text-red-400 py-8">
        Failed to load template: {error instanceof Error ? error.message : 'Unknown error'}
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div className="flex items-start gap-3">
        <Link to="/templates" className="text-zinc-500 hover:text-zinc-200 transition-colors mt-1">
          <ChevronLeft size={20} />
        </Link>
        <div className="min-w-0">
          <Badge intent="primary">{template.provider}</Badge>
          <h1 className="text-2xl font-semibold text-zinc-100 mt-2 tracking-tight">{template.name}</h1>
          <p className="text-sm text-zinc-400 mt-1">{template.description}</p>
        </div>
      </div>

      {/* Auto Deploy — only for AWS EC2 templates */}
      {template.provider === 'aws' && <AutoDeployPanel />}

      <Card>
        <CardHeader title="Manual Deploy" subtitle="Set variables and run a plan" />
        <CardBody>
          <TemplateDeployForm template={template} />
        </CardBody>
      </Card>
    </div>
  )
}

// --- Browser grid with provider filter ---
function TemplateBrowserGrid() {
  const [provider, setProvider] = useState<string | undefined>(undefined)
  const { data: templates, isLoading, error } = useTemplates(provider)

  const allTemplates = templates ?? []
  const providers = Array.from(new Set(allTemplates.map(t => t.provider)))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-zinc-100 tracking-tight">Templates</h1>
          <p className="text-sm text-zinc-400 mt-1">Browse and deploy infrastructure templates</p>
        </div>
        {isLoading && <Loader2 size={16} className="animate-spin text-zinc-500" />}
      </div>

      {/* Provider filter pills */}
      {providers.length > 1 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setProvider(undefined)}
            className={cn(
              'text-xs px-3 py-1 rounded-full border transition-colors duration-150',
              !provider
                ? 'bg-blue-500 border-blue-500 text-white'
                : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100',
            )}
          >
            All
          </button>
          {providers.map(p => (
            <button
              key={p}
              onClick={() => setProvider(p)}
              className={cn(
                'text-xs px-3 py-1 rounded-full border transition-colors duration-150',
                provider === p
                  ? 'bg-blue-500 border-blue-500 text-white'
                  : 'border-zinc-800 bg-zinc-900 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-100',
              )}
            >
              {p}
            </button>
          ))}
        </div>
      )}

      {error && (
        <p className="text-red-400 text-sm">
          Failed to load templates: {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      )}

      {!isLoading && allTemplates.length === 0 && !error && (
        <EmptyState title="No templates found" description="Try a different provider filter or check back later." />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {allTemplates.map(template => (
          <TemplateCard key={template.name} template={template} />
        ))}
      </div>
    </div>
  )
}

// --- Page entry point — routes between list and detail ---
export function TemplateBrowserPage() {
  const { provider, tplName } = useParams<{ provider?: string; tplName?: string }>()
  const fullName = provider && tplName ? `${provider}/${tplName}` : undefined
  return fullName ? <TemplateDetailView name={fullName} /> : <TemplateBrowserGrid />
}
