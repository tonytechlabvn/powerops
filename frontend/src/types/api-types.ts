// TypeScript interfaces matching the PowerOps backend API

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type JobType = 'plan' | 'apply' | 'destroy'
export type ApprovalStatus = 'pending' | 'approved' | 'rejected'
export type ResourceAction = 'create' | 'update' | 'delete' | 'no-op' | 'replace'
export type PermissionLevel = 'read' | 'plan' | 'write' | 'admin'
export type PolicyEnforcement = 'advisory' | 'soft-mandatory' | 'hard-mandatory'

export interface Job {
  id: string
  type: JobType
  status: JobStatus
  workspace: string
  created_at: string
  completed_at: string | null
  output: string | null
  error: string | null
  is_hidden: boolean
  vcs_commit_sha?: string | null
  vcs_pr_number?: number | null
  vcs_trigger?: string | null
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
  policy_override?: boolean
  policy_override_reason?: string
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

// --- Phase 1: State ---
export interface StateVersion {
  id: string
  serial: number
  lineage: string
  checksum: string
  resource_count?: number
  created_at: string
  created_by: string
}

export interface StateLockInfo {
  ID: string
  Operation: string
  Info: string
  Who: string
  Created: string
  Path: string
}

// --- Phase 2: Auth & RBAC ---
export interface AuthUser {
  id: string
  email: string
  name: string
  is_active: boolean
  created_at: string
  teams: string[]
  roles: string[]
}

export interface TeamInfo {
  id: string
  name: string
  is_admin: boolean
  member_count: number
}

export interface OrgInfo {
  id: string
  name: string
  created_at: string
}

export interface APITokenInfo {
  id: string
  name: string
  created_at: string
  last_used_at: string | null
  revoked_at: string | null
}

export interface APITokenCreated {
  id: string
  name: string
  token: string
}

// --- Phase 3: VCS ---
export interface VCSConnection {
  id: string
  workspace_id: string
  repo_full_name: string
  branch: string
  working_directory: string
  auto_apply: boolean
  created_at: string
}

// --- Phase 4: Policies ---
export interface PolicyInfo {
  id: string
  name: string
  description: string
  enforcement: PolicyEnforcement
  created_at: string
  updated_at: string
}

export interface PolicySetInfo {
  id: string
  name: string
  description: string
  scope: string
  policy_count: number
  created_at: string
}

export interface PolicyCheckResult {
  id: string
  policy_name: string
  enforcement: PolicyEnforcement
  passed: boolean
  violations: Array<{ resource: string; message: string; severity: string }>
  evaluated_at: string
}

export interface PolicyTestResult {
  violations: Array<{ resource: string; message: string; severity: string }>
  warnings: Array<{ resource: string; message: string; severity: string }>
  passed: boolean
}
