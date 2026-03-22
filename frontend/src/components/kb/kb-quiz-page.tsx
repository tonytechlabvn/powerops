// Full quiz page: question list, submit, result panel with pass/fail feedback

import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { CheckCircle, XCircle, RotateCcw, FlaskConical, ChevronRight } from 'lucide-react'
import { useKBQuiz, useSubmitQuiz } from '../../hooks/use-kb'
import { KBQuizQuestion } from './kb-quiz-question'
import type { QuizResult } from '../../types/kb-types'

const PASSING_SCORE = 70

export function KBQuizPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  const { data, isLoading, error } = useKBQuiz(slug)
  const submitQuiz = useSubmitQuiz()

  const [answers, setAnswers] = useState<Record<number, number | boolean>>({})
  const [result, setResult] = useState<QuizResult | null>(null)

  const questions = data?.questions ?? []
  const allAnswered = questions.length > 0 && questions.every((q) => answers[q.id] !== undefined)

  function handleAnswer(id: number, value: number | boolean) {
    setAnswers((prev) => ({ ...prev, [id]: value }))
  }

  async function handleSubmit() {
    try {
      const res = await submitQuiz.mutateAsync({ slug, answers })
      setResult(res)
    } catch {
      // error handled by mutation state
    }
  }

  function handleRetake() {
    setAnswers({})
    setResult(null)
  }

  if (isLoading) {
    return <div className="flex items-center justify-center h-64 text-zinc-500">Loading quiz...</div>
  }

  if (error || !data) {
    return <div className="flex items-center justify-center h-64 text-red-400">Failed to load quiz.</div>
  }

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 text-xs text-zinc-500">
        <Link to="/kb" className="hover:text-zinc-300 transition-colors">Knowledge Base</Link>
        <ChevronRight size={12} />
        <Link to={`/kb/${slug}`} className="hover:text-zinc-300 transition-colors capitalize">
          {slug.replace(/-/g, ' ')}
        </Link>
        <ChevronRight size={12} />
        <span className="text-zinc-300">Quiz</span>
      </div>

      {/* Header */}
      <div className="space-y-1">
        <h1 className="text-xl font-bold text-zinc-100">Chapter Quiz</h1>
        <p className="text-zinc-400 text-sm">
          {questions.length} questions — passing score {PASSING_SCORE}%
        </p>
      </div>

      {/* Result banner */}
      {result && (
        <div className={`border rounded-lg p-5 space-y-3 ${result.passed ? 'bg-green-500/10 border-green-500/40' : 'bg-red-500/10 border-red-500/40'}`}>
          <div className="flex items-center gap-3">
            {result.passed
              ? <CheckCircle size={22} className="text-green-400" />
              : <XCircle size={22} className="text-red-400" />}
            <div>
              <p className={`font-semibold ${result.passed ? 'text-green-300' : 'text-red-300'}`}>
                {result.passed ? 'Passed!' : 'Not quite — try again'}
              </p>
              <p className="text-sm text-zinc-400">
                Score: <span className="text-zinc-200 font-medium">{result.score}%</span>
                {' '}({result.correct_count}/{result.total} correct)
              </p>
            </div>
          </div>
          <div className="flex gap-3 pt-1">
            <button
              onClick={handleRetake}
              className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm transition-colors"
            >
              <RotateCcw size={13} /> Retake
            </button>
            {result.passed && (
              <Link
                to={`/kb/${slug}/lab`}
                className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm transition-colors"
              >
                <FlaskConical size={13} /> Continue to Lab
              </Link>
            )}
          </div>
        </div>
      )}

      {/* Questions */}
      <div className="space-y-4">
        {questions.map((q) => {
          const detail = result?.details.find((d) => d.id === q.id)
          return (
            <KBQuizQuestion
              key={q.id}
              question={q}
              answer={answers[q.id]}
              onChange={(val) => handleAnswer(q.id, val)}
              showResult={!!result}
              result={detail ? { correct: detail.correct, explanation: detail.explanation } : undefined}
            />
          )
        })}
      </div>

      {/* Submit */}
      {!result && (
        <button
          onClick={handleSubmit}
          disabled={!allAnswered || submitQuiz.isPending}
          className="w-full py-2.5 rounded-md bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium text-sm transition-colors"
        >
          {submitQuiz.isPending ? 'Submitting...' : 'Submit Quiz'}
        </button>
      )}

      {submitQuiz.isError && (
        <p className="text-red-400 text-xs text-center">Submission failed — please try again.</p>
      )}
    </div>
  )
}
