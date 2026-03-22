// KB chapter content reader with sidebar nav, sections, HCL blocks, and action buttons

import { useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { BookOpen, FlaskConical, ChevronRight, Clock } from 'lucide-react'
import { useKBChapter, useKBCurriculum, useStartChapter } from '../../hooks/use-kb'
import { KBChapterNav } from './kb-chapter-nav'
import { KBFeatureLinks } from './kb-feature-link'
import type { ContentSection } from '../../types/kb-types'

function HclBlock({ code }: { code: string }) {
  return (
    <pre className="bg-zinc-950 border border-zinc-800 rounded-md p-4 text-xs font-mono text-green-300 overflow-x-auto whitespace-pre leading-relaxed">
      {code}
    </pre>
  )
}

function Section({ section }: { section: ContentSection }) {
  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold text-zinc-100 border-b border-zinc-800 pb-2">
        {section.title}
      </h2>
      <p className="text-zinc-300 text-sm leading-relaxed whitespace-pre-wrap">{section.body}</p>
      {section.hcl_example && <HclBlock code={section.hcl_example} />}
    </div>
  )
}

export function KBChapterPage() {
  const { slug = '' } = useParams<{ slug: string }>()
  const { data: chapter, isLoading, error } = useKBChapter(slug)
  const { data: curriculum } = useKBCurriculum()
  const startChapter = useStartChapter()

  // Auto-mark chapter as started on mount
  useEffect(() => {
    if (slug) startChapter.mutate(slug)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [slug])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-zinc-500">
        Loading chapter...
      </div>
    )
  }

  if (error || !chapter) {
    return (
      <div className="flex items-center justify-center h-64 text-red-400">
        Chapter not found.
      </div>
    )
  }

  const chapters = curriculum?.chapters ?? []

  return (
    <div className="flex h-full min-h-screen bg-zinc-950">
      {/* Left nav */}
      <aside className="hidden md:flex flex-col w-60 shrink-0 border-r border-zinc-800 p-4 overflow-y-auto">
        <KBChapterNav chapters={chapters} currentSlug={slug} />
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto p-6 max-w-3xl space-y-6">
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 text-xs text-zinc-500">
          <Link to="/kb" className="hover:text-zinc-300 transition-colors">Knowledge Base</Link>
          <ChevronRight size={12} />
          <span className="text-zinc-300">{chapter.title}</span>
        </div>

        {/* Chapter header */}
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <span className="text-xs text-zinc-600 font-mono">
              {String(chapter.order).padStart(2, '0')}
            </span>
            <h1 className="text-2xl font-bold text-zinc-100">{chapter.title}</h1>
          </div>
          <div className="flex items-center gap-4 text-xs text-zinc-500">
            <span className="capitalize">{chapter.difficulty}</span>
            <span className="flex items-center gap-1">
              <Clock size={12} /> {chapter.estimated_minutes} min
            </span>
          </div>
          {chapter.concepts.length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {chapter.concepts.map((c) => (
                <span key={c} className="px-2 py-0.5 bg-zinc-800 text-zinc-400 text-xs rounded-full">
                  {c}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Sections */}
        <div className="space-y-8">
          {chapter.content.sections.map((section, i) => (
            <Section key={i} section={section} />
          ))}
        </div>

        {/* PowerOps deep integration links */}
        {chapter.powerops_features.length > 0 && (
          <KBFeatureLinks features={chapter.powerops_features} />
        )}

        {/* Action buttons */}
        <div className="flex gap-3 pt-4 border-t border-zinc-800">
          <Link
            to={`/kb/${slug}/quiz`}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
          >
            <BookOpen size={15} /> Take Quiz
          </Link>
          <Link
            to={`/kb/${slug}/lab`}
            className="flex items-center gap-2 px-4 py-2 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-sm font-medium transition-colors"
          >
            <FlaskConical size={15} /> Start Lab
          </Link>
        </div>
      </main>
    </div>
  )
}
