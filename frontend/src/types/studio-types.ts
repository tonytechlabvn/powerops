// TypeScript types for the AI Template Studio feature.

export type StudioMode = 'creator' | 'extractor' | 'wizard' | 'canvas'

export interface StudioTemplate {
  name: string
  providers: string[]
  description: string
  display_name: string
  files: Record<string, string>
  tags: string[]
  version: string
  validation?: StudioValidation | null
}

export interface StudioValidation {
  valid: boolean
  jinja2_errors: string[]
  hcl_errors: Record<string, string[]>
  structure_warnings: string[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export type StudioStatus = 'idle' | 'generating' | 'extracting' | 'refining' | 'saving' | 'done' | 'error'

// Phase 4: Wizard types
export type WizardStepId = 'provider' | 'compute' | 'networking' | 'storage'
  | 'security' | 'connectivity' | 'monitoring' | 'review'

export interface WizardStepConfig {
  id: WizardStepId
  label: string
  optional: boolean
  defaults: Record<string, unknown>
}

export interface WizardState {
  steps: WizardStepConfig[]
  currentStep: number
  stepData: Record<string, Record<string, unknown>>
  reasoning: string
}
