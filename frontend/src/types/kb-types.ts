// TypeScript interfaces for the Knowledge Base module, matching backend API schemas

export interface ChapterSummary {
  slug: string
  title: string
  order: number
  difficulty: 'beginner' | 'intermediate' | 'advanced'
  estimated_minutes: number
  prerequisites: string[]
  concepts: string[]
  description: string
  status: 'not_started' | 'in_progress' | 'completed'
  quiz_score: number | null
  lab_completed: boolean
}

export interface ContentSection {
  title: string
  body: string
  hcl_example?: string
}

export interface ChapterDetail {
  slug: string
  title: string
  order: number
  difficulty: string
  estimated_minutes: number
  prerequisites: string[]
  concepts: string[]
  powerops_features: string[]
  content: { sections: ContentSection[] }
}

export interface QuizQuestion {
  id: number
  type: 'multiple_choice' | 'true_false'
  question: string
  options?: string[]
}

export interface QuizResult {
  score: number
  passed: boolean
  total: number
  correct_count: number
  details: Array<{
    id: number
    correct: boolean
    user_answer: number | boolean
    correct_answer: number | boolean
    explanation: string
  }>
}

export interface LabInfo {
  chapter_slug: string
  title: string
  description: string
  instructions: string
  starter_hcl: string
  hints: string[]
  recommended_level: string
  available_levels: string[]
}

export interface ValidationMessage {
  level: string
  pattern?: string
  passed: boolean
  message: string
}

export interface LabValidationResult {
  level: string
  passed: boolean
  messages: ValidationMessage[]
}

export interface UserProgress {
  total_chapters: number
  completed: number
  in_progress: number
  not_started: number
  avg_quiz_score: number | null
  chapters: ChapterSummary[]
}

export interface GlossaryConcept {
  term: string
  one_line: string
  explanation?: string
  example?: string
  related_concepts?: string[]
}

export interface LeaderboardEntry {
  user_id: string
  display_name: string
  chapters_completed: number
  avg_quiz_score: number
  labs_completed: number
  total_score: number
  badges: string[]
}

export interface LeaderboardResponse {
  scope: string
  entries: LeaderboardEntry[]
  current_user_rank: number | null
}
