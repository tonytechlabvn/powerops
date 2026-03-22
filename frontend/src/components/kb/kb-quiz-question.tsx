// Single quiz question: MCQ radio buttons or true/false toggle with result feedback

import { cn } from '../../lib/utils'
import type { QuizQuestion } from '../../types/kb-types'

interface QuestionResult {
  correct: boolean
  explanation: string
}

interface KBQuizQuestionProps {
  question: QuizQuestion
  answer: number | boolean | undefined
  onChange: (value: number | boolean) => void
  showResult?: boolean
  result?: QuestionResult
}

export function KBQuizQuestion({
  question,
  answer,
  onChange,
  showResult = false,
  result,
}: KBQuizQuestionProps) {
  const borderColor = showResult && result
    ? result.correct ? 'border-green-500/50' : 'border-red-500/50'
    : 'border-zinc-800'

  return (
    <div className={cn('bg-zinc-900 border rounded-lg p-4 space-y-3', borderColor)}>
      <p className="text-zinc-100 text-sm font-medium leading-relaxed">{question.question}</p>

      {question.type === 'multiple_choice' && question.options && (
        <div className="space-y-2">
          {question.options.map((opt, idx) => {
            const isSelected = answer === idx
            const optBorder = showResult && isSelected
              ? result?.correct ? 'border-green-500 bg-green-500/10' : 'border-red-500 bg-red-500/10'
              : isSelected
                ? 'border-blue-500 bg-blue-500/10'
                : 'border-zinc-700 hover:border-zinc-500'

            return (
              <label
                key={idx}
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md border cursor-pointer transition-colors text-sm',
                  optBorder,
                  showResult && 'cursor-default',
                )}
              >
                <input
                  type="radio"
                  name={`q-${question.id}`}
                  value={idx}
                  checked={isSelected}
                  onChange={() => !showResult && onChange(idx)}
                  className="accent-blue-500"
                  disabled={showResult}
                />
                <span className="text-zinc-300">{opt}</span>
              </label>
            )
          })}
        </div>
      )}

      {question.type === 'true_false' && (
        <div className="flex gap-3">
          {([true, false] as const).map((val) => {
            const isSelected = answer === val
            const btnStyle = showResult && isSelected
              ? result?.correct ? 'border-green-500 bg-green-500/10 text-green-300' : 'border-red-500 bg-red-500/10 text-red-300'
              : isSelected
                ? 'border-blue-500 bg-blue-500/10 text-blue-300'
                : 'border-zinc-700 text-zinc-400 hover:border-zinc-500 hover:text-zinc-200'

            return (
              <button
                key={String(val)}
                onClick={() => !showResult && onChange(val)}
                disabled={showResult}
                className={cn(
                  'px-6 py-2 rounded-md border text-sm font-medium transition-colors',
                  btnStyle,
                )}
              >
                {val ? 'True' : 'False'}
              </button>
            )
          })}
        </div>
      )}

      {showResult && result && (
        <p className={cn('text-xs mt-2 leading-relaxed', result.correct ? 'text-green-400' : 'text-red-400')}>
          {result.correct ? 'Correct — ' : 'Incorrect — '}{result.explanation}
        </p>
      )}
    </div>
  )
}
