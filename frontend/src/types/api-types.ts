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

// --- Phase 5: Projects ---
export type ProjectStatus = 'draft' | 'active' | 'archived'
export type ModuleStatus = 'pending' | 'planning' | 'applying' | 'applied' | 'failed'

export interface ProjectModule {
  id: string
  name: string
  path: string
  provider: string
  depends_on: string[]
  status: ModuleStatus
  last_run_id: string | null
}

export interface ProjectMember {
  user_id: string
  user_email: string
  user_name: string
  role_name: string
  assigned_modules: string[]
  joined_at: string
}

export interface ProjectRun {
  id: string
  module_id: string
  module_name: string
  user_id: string
  run_type: string
  status: string
  started_at: string
  completed_at: string | null
}

export interface ProjectCredential {
  id: string
  provider: string
  is_sensitive: boolean
  created_by: string
  created_at: string
}

export interface ProjectSummary {
  id: string
  name: string
  description: string
  status: ProjectStatus
  created_by: string
  created_at: string
  updated_at: string
  module_count: number
  member_count: number
}

export interface ProjectDetail extends ProjectSummary {
  config_yaml: string
  org_id: string | null
  modules: ProjectModule[]
  members: ProjectMember[]
  runs: ProjectRun[]
}

// --- Phase 5 (extended): Project Activity Feed ---
export interface ProjectActivity {
  id: string
  project_id: string
  user_id: string
  action: string
  module_id: string | null
  details_json: string
  created_at: string
}

// --- HCL File Management (Standard Workflow Phase 1) ---

export interface FileInfo {
  path: string
  name: string
  size: number
  modified_at: string
  is_directory: boolean
  checksum: string
}

export interface FileContent {
  path: string
  content: string
  checksum: string
  size: number
  language: string
}

export interface WriteFileResponse {
  path: string
  checksum: string
  validation: FileValidationResult | null
}

export interface FileValidationResult {
  valid: boolean
  errors: string[]
  warnings: string[]
}

export interface FileSearchResult {
  path: string
  line: number
  content: string
  context_before: string
  context_after: string
}

// Alias for backward compat
export type SearchResult = FileSearchResult

// --- Environments (Standard Workflow Phase 2) ---

export interface Environment {
  id: string
  org_id: string
  name: string
  description: string
  order: number
  auto_apply: boolean
  require_approval: boolean
  is_protected?: boolean
  color?: string
  created_at: string
  variable_count: number
  workspace_count: number
}

export interface EnvironmentInfo {
  id: string
  org_id: string
  name: string
  description: string
  order: number
  auto_apply: boolean
  require_approval: boolean
  created_at: string
  variable_count: number
  workspace_count: number
}

export interface EnvironmentVariable {
  id: string
  key: string
  value: string
  category: 'terraform' | 'env'
  is_sensitive: boolean
  is_hcl: boolean
}

export interface EffectiveVariable {
  key: string
  value: string
  category: string
  source: 'environment' | 'workspace' | 'variable_set'
  is_sensitive: boolean
}

// --- Variable Sets (Standard Workflow Phase 3) ---

export interface VariableSet {
  id: string
  org_id: string
  name: string
  description: string
  is_global: boolean
  created_at: string
  updated_at: string
  variable_count: number
  workspace_count: number
  variables: VariableSetVariable[]
}

export interface VariableSetInfo {
  id: string
  org_id: string
  name: string
  description: string
  is_global: boolean
  created_at: string
  updated_at: string
  variable_count: number
  workspace_count: number
}

export interface VariableSetVariable {
  id: string
  key: string
  value: string
  category: 'terraform' | 'env'
  is_sensitive: boolean
  is_hcl: boolean
  description?: string
  variable_set_id?: string
}

// --- VCS Workflow (Standard Workflow Phase 4) ---

export interface TriggerPattern {
  pattern?: string
  branch?: string
  action: 'include' | 'exclude' | 'plan' | 'apply'
}

export interface VCSWorkflowConfig {
  auto_plan: boolean
  auto_apply: boolean
  trigger_patterns: TriggerPattern[]
  repo_full_name?: string
  branch?: string
}

export interface VCSPlanRun {
  id: string
  workspace_id: string
  commit_sha: string
  branch: string
  pr_number: number | null
  run_type: string
  status: string
  adds: number
  changes: number
  destroys: number
  plan_output: string
  plan_summary_json?: string
  error_output: string
  triggered_at?: string
  policy_passed?: boolean
  created_at: string
  completed_at: string | null
}

// --- Module Registry (Standard Workflow Phase 5-7) ---

export interface RegistryModule {
  id: string
  namespace: string
  name: string
  provider: string
  description: string
  is_deprecated: boolean
  download_count: number
  latest_version: string | null
  version_count?: number
  versions?: RegistryModuleVersion[]
  tags?: string[]
  created_at: string
  updated_at: string
}

export interface PublishModuleRequest {
  namespace: string
  name: string
  provider: string
  description?: string
  tags?: string[]
}

export interface ModuleVersionDetail extends RegistryModuleVersion {
  module?: RegistryModule
  variables?: VariableDoc[]
  outputs?: OutputDoc[]
  resources?: Array<{ type: string; name: string; provider?: string; address?: string }>
  readme?: string
  usage_example?: string
}

export interface StackDefinition {
  modules: StackModuleEntry[]
  variables?: Record<string, string>
  name?: string
}

export interface RegistryModuleVersion {
  id: string
  version: string
  readme_content: string
  variables_json: string
  outputs_json: string
  resources_json: string
  published_by: string
  published_at: string
}

export interface VariableDoc {
  name: string
  type: string
  description: string
  default: string | null
  required: boolean
}

export interface OutputDoc {
  name: string
  description: string
  value: string
}

export interface ResourceDoc {
  type: string
  name: string
  address: string
}

export interface StackModuleEntry {
  module_id: string
  version: string
  alias: string
  name?: string
  source?: string
  variables: Record<string, string>
  depends_on: string[]
}

export interface StackTemplate {
  id: string
  name: string
  description: string
  definition: StackModuleEntry[]
  definition_json?: string
  module_count?: number
  tags?: string[]
  created_by: string
  created_at: string
  updated_at: string
}

export interface ComposeResult {
  main_tf: string
  variables_tf: string
  outputs_tf: string
  generated_files?: Record<string, string>
  warnings?: string[]
  project_id?: string
}

export interface UpgradeInfo {
  module_id: string
  module_name: string
  current_version: string
  latest_version: string
  source?: string
}

// --- Phase 8: AI Editor ---

export interface AICompletionResponse {
  suggestion: string
  confidence: number
}

// --- Phase 9: AI Plan Explainer ---

export interface PlanRiskFlag {
  type: 'data_loss' | 'downtime' | 'security' | string
  resource: string
  reason: string
}

export interface PlanRiskAssessment {
  level: 'low' | 'medium' | 'high' | 'critical' | string
  flags: PlanRiskFlag[]
}

export interface PlanCostImpact {
  direction: 'increase' | 'decrease' | 'neutral' | string
  estimate: string
}

export interface PlanSummaryStats {
  total_changes: number
  creates: number
  updates: number
  destroys: number
  replacements: number
  resource_types: string[]
  affected_modules: string[]
}

export interface PlanAnalysisResponse {
  summary: PlanSummaryStats
  risk: PlanRiskAssessment
  cost: PlanCostImpact
}

// --- Phase 10: AI Remediation ---

export interface ErrorCategoryInfo {
  type: string
  is_code_fixable: boolean
  severity: string
}

export interface FileFix {
  file_path: string
  original_content: string
  fixed_content: string
  diff_lines: string[]
  description: string
}

export interface RemediationResponse {
  error_category: ErrorCategoryInfo
  root_cause: string
  is_fixable: boolean
  fixes: FileFix[]
  explanation: string
  confidence: number
}

export interface ApplyFixResponse {
  applied: string[]
  failed: string[]
  validation_errors: string[]
}

// --- Phase 11: AI Module Generator ---

export interface ModuleValidationResponse {
  valid: boolean
  file_errors: Record<string, string[]>
  structure_warnings: string[]
}

export interface GeneratedModuleResponse {
  name: string
  provider: string
  description: string
  files: Record<string, string>
  resources: string[]
  validation: ModuleValidationResponse | null
}
