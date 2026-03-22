// AI remediation panel — shown when a job or validation fails.
// Fetches diagnosis, displays root cause + fix diffs, allows one-click apply.

import { useState } from 'react'
import { apiClient } from '../../services/api-client'
import { FixDiffViewer } from './fix-diff-viewer'
import type { RemediationResponse, ApplyFixResponse } from '../../types/api-types'

interface RemediationPanelProps {
  workspaceId: string
  errorOutput: string
  failedOperation?: string
  jobId?: string               // if remediating a specific job
  onFixApplied?: () => void    // callback to re-trigger plan/validation
}

const CATEGORY_LABELS: Record<string, string> = {
  hcl_syntax: 'HCL Syntax Error',
  missing_attribute: 'Missing Attribute',
  invalid_resource: 'Invalid Resource Type',
  permission: 'Permission Denied',
  state: 'State Conflict',
  provider: 'Provider Configuration',
  unknown: 'Unknown Error',
}

export function RemediationPanel({
  workspaceId,
  errorOutput,
  failedOperation = 'plan',
  jobId,
  onFixApplied,
}: RemediationPanelProps) {
  const [diagnosis, setDiagnosis] = useState<RemediationResponse | null>(null)
  const [diagnosing, setDiagnosing] = useState(false)
  const [applying, setApplying] = useState(false)
  const [applyResult, setApplyResult] = useState<ApplyFixResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleDiagnose = async () => {
    setDiagnosing(true)
    setError(null)
    setDiagnosis(null)
    setApplyResult(null)
    try {
      let result: RemediationResponse
      if (jobId) {
        result = await apiClient.post<RemediationResponse>(
          `/api/jobs/${jobId}/remediate`,
          { workspace_id: workspaceId },
        )
      } else {
        result = await apiClient.post<RemediationResponse>(
          `/api/workspaces/${workspaceId}/remediate`,
          { error_output: errorOutput, workspace_id: workspaceId, failed_operation: failedOperation },
        )
      }
      setDiagnosis(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Diagnosis failed')
    } finally {
      setDiagnosing(false)
    }
  }

  const handleApplyFix = async () => {
    if (!diagnosis?.fixes.length) return
    setApplying(true)
    setError(null)
    try {
      const result = await apiClient.post<ApplyFixResponse>(
        `/api/workspaces/${workspaceId}/remediate/apply`,
        {
          workspace_id: workspaceId,
          fixes: diagnosis.fixes.map(f => ({
            file_path: f.file_path,
            fixed_content: f.fixed_content,
            description: f.description,
          })),
        },
      )
      setApplyResult(result)
      if (result.applied.length > 0) onFixApplied?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Apply failed')
    } finally {
      setApplying(false)
    }
  }

  const confidenceColor = (c: number) =>
    c >= 0.8 ? 'text-green-400' : c >= 0.5 ? 'text-yellow-400' : 'text-red-400'

  return (
    <div className="border border-zinc-800 rounded-lg bg-zinc-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-800">
        <span className="text-zinc-200 font-medium text-sm">AI Remediation</span>
        <button
          onClick={handleDiagnose}
          disabled={diagnosing}
          className="px-3 py-1 bg-blue-700 hover:bg-blue-600 disabled:opacity-40
                     text-white text-xs rounded font-medium transition-colors"
        >
          {diagnosing ? 'Diagnosing…' : diagnosis ? 'Re-diagnose' : 'Diagnose Error'}
        </button>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {!diagnosis && !diagnosing && (
          <p className="text-zinc-500 text-xs">
            Click "Diagnose Error" to analyze the failure and get suggested fixes.
          </p>
        )}

        {diagnosing && (
          <div className="flex gap-1.5 items-center text-zinc-400 text-xs">
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-bounce [animation-delay:300ms]" />
            <span className="ml-1">Analyzing error with AI…</span>
          </div>
        )}

        {diagnosis && (
          <>
            {/* Category + fixability */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="px-2 py-0.5 bg-zinc-800 border border-zinc-700 rounded
                               text-zinc-300 text-xs font-medium">
                {CATEGORY_LABELS[diagnosis.error_category.type] ?? diagnosis.error_category.type}
              </span>
              <span className={`text-xs font-medium ${
                diagnosis.is_fixable ? 'text-green-400' : 'text-red-400'
              }`}>
                {diagnosis.is_fixable ? '✓ Code-fixable' : '✕ Requires manual action'}
              </span>
              <span className={`text-xs ${confidenceColor(diagnosis.confidence)}`}>
                {Math.round(diagnosis.confidence * 100)}% confidence
              </span>
            </div>

            {/* Root cause */}
            <div>
              <h4 className="text-zinc-400 text-xs font-medium uppercase tracking-wide mb-1">Root Cause</h4>
              <p className="text-zinc-200 text-sm">{diagnosis.root_cause}</p>
            </div>

            {/* Explanation */}
            {diagnosis.explanation && (
              <div>
                <h4 className="text-zinc-400 text-xs font-medium uppercase tracking-wide mb-1">Explanation</h4>
                <p className="text-zinc-400 text-xs leading-relaxed">{diagnosis.explanation}</p>
              </div>
            )}

            {/* Fix diffs */}
            {diagnosis.fixes.length > 0 && (
              <div className="space-y-3">
                <h4 className="text-zinc-400 text-xs font-medium uppercase tracking-wide">Suggested Fixes</h4>
                {diagnosis.fixes.map((fix, i) => (
                  <FixDiffViewer
                    key={i}
                    filePath={fix.file_path}
                    diffLines={fix.diff_lines}
                    description={fix.description}
                  />
                ))}
                <button
                  onClick={handleApplyFix}
                  disabled={applying || !!applyResult}
                  className="px-4 py-1.5 bg-green-700 hover:bg-green-600 disabled:opacity-40
                             text-white text-sm rounded font-medium transition-colors"
                >
                  {applying ? 'Applying…' : 'Apply Fix'}
                </button>
              </div>
            )}

            {/* Apply result */}
            {applyResult && (
              <div className="bg-zinc-950 rounded p-3 text-xs space-y-1">
                {applyResult.applied.map(p => (
                  <p key={p} className="text-green-400">✓ Applied: {p}</p>
                ))}
                {applyResult.failed.map(p => (
                  <p key={p} className="text-red-400">✕ Failed: {p}</p>
                ))}
                {applyResult.validation_errors.map((e, i) => (
                  <p key={i} className="text-yellow-400">⚠ {e}</p>
                ))}
              </div>
            )}
          </>
        )}

        {error && <p className="text-red-400 text-xs">{error}</p>}
      </div>
    </div>
  )
}
