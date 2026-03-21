// Display deployment outputs (IPs, DNS, resource IDs) from completed apply jobs

import { CheckCircle, ExternalLink, Copy } from 'lucide-react'
import type { Job } from '../../types/api-types'

interface JobOutputSummaryProps {
  job: Job
}

// Parse terraform JSON output lines to extract useful info
function parseOutputs(output: string): Record<string, string> {
  const outputs: Record<string, string> = {}

  // Check for "--- OUTPUTS ---" section appended by deploy route
  const outputSection = output.split('--- OUTPUTS ---')
  if (outputSection.length > 1) {
    const lines = outputSection[1].trim().split('\n')
    for (const line of lines) {
      const match = line.match(/^\s*(\S+)\s*=\s*(.+)$/)
      if (match) outputs[match[1]] = match[2].trim()
    }
  }

  // Also parse JSON lines for terraform outputs
  for (const line of output.split('\n')) {
    try {
      const parsed = JSON.parse(line)
      if (parsed.type === 'outputs' && parsed.outputs) {
        for (const [key, val] of Object.entries(parsed.outputs)) {
          const v = val as { value?: string }
          if (v.value) outputs[key] = String(v.value)
        }
      }
    } catch {
      // not JSON, skip
    }
  }

  return outputs
}

function isUrl(value: string): boolean {
  return /^https?:\/\//.test(value) || /\.(com|net|org|io|dev)/.test(value)
}

function isIp(value: string): boolean {
  return /^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(value)
}

export function JobOutputSummary({ job }: JobOutputSummaryProps) {
  if (job.status !== 'completed' || !job.output) return null

  const outputs = parseOutputs(job.output)
  const hasOutputs = Object.keys(outputs).length > 0

  // Check if apply succeeded from JSON output
  const isApply = job.type === 'apply'
  const hasApplyComplete = job.output.includes('"type":"apply_complete"') ||
    job.output.includes('[apply] Deployment completed')

  if (!hasOutputs && !hasApplyComplete) return null

  return (
    <div className="rounded-lg border border-green-500/30 bg-green-500/5 p-5 space-y-4">
      <div className="flex items-center gap-2">
        <CheckCircle size={18} className="text-green-400" />
        <h2 className="text-sm font-semibold text-green-400">
          {isApply ? 'Deployment Complete' : 'Plan Complete'}
        </h2>
      </div>

      {hasOutputs && (
        <div className="space-y-2">
          <p className="text-xs text-zinc-400 uppercase tracking-wider">Resource Outputs</p>
          <div className="rounded border border-zinc-800 bg-zinc-950 overflow-hidden">
            {Object.entries(outputs).map(([key, value]) => (
              <div
                key={key}
                className="flex items-center justify-between px-4 py-2.5 border-b border-zinc-800 last:border-0"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <span className="text-xs font-medium text-zinc-300">{key}</span>
                  {isIp(value) && (
                    <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/20 text-blue-400 border border-blue-500/30">
                      IP
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-mono text-zinc-100">{value}</span>
                  {isUrl(value) && (
                    <a
                      href={value.startsWith('http') ? value : `http://${value}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:text-blue-300"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}
                  <button
                    onClick={() => navigator.clipboard.writeText(value)}
                    className="text-zinc-500 hover:text-zinc-300 transition-colors"
                    title="Copy to clipboard"
                  >
                    <Copy size={14} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasOutputs && hasApplyComplete && (
        <p className="text-sm text-zinc-300">
          Infrastructure deployed successfully. No outputs defined in the template.
        </p>
      )}
    </div>
  )
}
