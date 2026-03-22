// React Query hooks for the Knowledge Base module API endpoints

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { apiClient } from '../services/api-client'
import type {
  UserProgress,
  ChapterDetail,
  QuizQuestion,
  QuizResult,
  LabInfo,
  LabValidationResult,
  GlossaryConcept,
  LeaderboardResponse,
} from '../types/kb-types'

// --- Query keys ---
export const kbKeys = {
  curriculum: () => ['kb', 'curriculum'] as const,
  chapter: (slug: string) => ['kb', 'chapter', slug] as const,
  quiz: (slug: string) => ['kb', 'quiz', slug] as const,
  lab: (slug: string) => ['kb', 'lab', slug] as const,
  progress: () => ['kb', 'progress'] as const,
  leaderboard: (scope: string) => ['kb', 'leaderboard', scope] as const,
  glossary: () => ['kb', 'glossary'] as const,
  glossaryTerm: (term: string) => ['kb', 'glossary', term] as const,
}

// --- Read hooks ---

export function useKBCurriculum() {
  return useQuery({
    queryKey: kbKeys.curriculum(),
    queryFn: () => apiClient.get<UserProgress>('/api/kb/curriculum'),
  })
}

export function useKBChapter(slug: string) {
  return useQuery({
    queryKey: kbKeys.chapter(slug),
    queryFn: () => apiClient.get<ChapterDetail>(`/api/kb/chapters/${slug}`),
    enabled: !!slug,
  })
}

export function useKBQuiz(slug: string) {
  return useQuery({
    queryKey: kbKeys.quiz(slug),
    queryFn: () => apiClient.get<{ questions: QuizQuestion[] }>(`/api/kb/chapters/${slug}/quiz`),
    enabled: !!slug,
  })
}

export function useKBLab(slug: string) {
  return useQuery({
    queryKey: kbKeys.lab(slug),
    queryFn: () => apiClient.get<LabInfo>(`/api/kb/chapters/${slug}/lab`),
    enabled: !!slug,
  })
}

export function useKBProgress() {
  return useQuery({
    queryKey: kbKeys.progress(),
    queryFn: () => apiClient.get<UserProgress>('/api/kb/progress'),
  })
}

export function useKBGlossary() {
  return useQuery({
    queryKey: kbKeys.glossary(),
    queryFn: () => apiClient.get<{ concepts: GlossaryConcept[] }>('/api/kb/glossary'),
  })
}

export function useKBLeaderboard(scope: string = 'global') {
  return useQuery({
    queryKey: kbKeys.leaderboard(scope),
    queryFn: () => apiClient.get<LeaderboardResponse>('/api/kb/leaderboard', { scope }),
  })
}

// --- Mutation hooks ---

export function useStartChapter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) =>
      apiClient.post<{ ok: boolean }>(`/api/kb/chapters/${slug}/start`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kbKeys.curriculum() })
      qc.invalidateQueries({ queryKey: kbKeys.progress() })
    },
  })
}

export function useSubmitQuiz() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ slug, answers }: { slug: string; answers: Record<number, number | boolean> }) =>
      apiClient.post<QuizResult>(`/api/kb/chapters/${slug}/quiz/submit`, { answers }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kbKeys.curriculum() })
      qc.invalidateQueries({ queryKey: kbKeys.progress() })
    },
  })
}

export function useValidateLab() {
  return useMutation({
    mutationFn: ({ slug, hcl, level }: { slug: string; hcl: string; level: string }) =>
      apiClient.post<LabValidationResult>(`/api/kb/chapters/${slug}/lab/validate`, { hcl, level }),
  })
}

export function useCompleteChapter() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (slug: string) =>
      apiClient.post<{ ok: boolean }>(`/api/kb/chapters/${slug}/complete`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: kbKeys.curriculum() })
      qc.invalidateQueries({ queryKey: kbKeys.progress() })
    },
  })
}
