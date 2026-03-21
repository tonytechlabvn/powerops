// TypeScript interfaces matching the TerraBot backend API

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type JobType = 'plan' | 'apply' | 'destroy'
export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type ResourceAction = 'create' | 'update' | 'delete' | 'no-op' | 'replace'

export interface Job {
  id: string
  type: JobType
  status: JobStatus
  workspace: string
  created_at: string
  completed_at: string | null
  output: string | null
  error: string | null
}

export interface TemplateVariable {
  name: string
  type: 'string' | 'number' | 'bool' | 'list' | 'map'
  description: string
  default: string | number | boolean | null
  required: boolean
}

export interface Template {
  name: string
  provider: string
  description: string
  tags: string[]
  variables: TemplateVariable[]
  estimated_cost: string | null
}

export interface ResourceChange {
  address: string
  type: string
  name: string
  action: ResourceAction
  before: Record<string, unknown> | null
  after: Record<string, unknown> | null
}

export interface PlanSummary {
  adds: number
  changes: number
  destroys: number
  resources: ResourceChange[]
  cost_estimate: string | null
}

export interface Approval {
  id: string
  job_id: string
  status: ApprovalStatus
  plan_summary: PlanSummary | null
  created_at: string
  decided_at: string | null
  reason: string | null
}

export interface ProviderConfig {
  provider: string
  config: Record<string, string>
}

export interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy'
  terraform_version: string
  db_status: string
  active_jobs: number
}

export interface ApiError {
  message: string
  status: number
  detail?: string
}
