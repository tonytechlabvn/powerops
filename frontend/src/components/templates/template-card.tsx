// Card displaying a single Terraform template with provider, tags, and deploy action

import { Link } from 'react-router-dom'
import { Tag, DollarSign } from 'lucide-react'
import type { Template } from '../../types/api-types'

interface TemplateCardProps {
  template: Template
}

export function TemplateCard({ template }: TemplateCardProps) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-5 flex flex-col gap-3 hover:border-zinc-700 transition-colors">
      {/* Provider badge + name */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="text-xs font-medium px-2 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
            {template.provider}
          </span>
          <h3 className="text-base font-semibold text-zinc-100 mt-2">{template.name}</h3>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-zinc-400 line-clamp-2">{template.description}</p>

      {/* Tags */}
      {template.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {template.tags.map(tag => (
            <span
              key={tag}
              className="flex items-center gap-1 text-xs text-zinc-500 bg-zinc-800 rounded px-1.5 py-0.5"
            >
              <Tag size={10} />
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Cost + deploy */}
      <div className="flex items-center justify-between mt-auto pt-2 border-t border-zinc-800">
        {template.estimated_cost ? (
          <span className="flex items-center gap-1 text-xs text-zinc-400">
            <DollarSign size={12} />
            {template.estimated_cost}
          </span>
        ) : (
          <span className="text-xs text-zinc-600">No cost estimate</span>
        )}
        <Link
          to={`/templates/${template.name}`}  /* name is already "aws/ec2-web-server" format */
          className="text-xs font-medium text-blue-400 hover:text-blue-300 transition-colors"
        >
          Deploy →
        </Link>
      </div>
    </div>
  )
}
