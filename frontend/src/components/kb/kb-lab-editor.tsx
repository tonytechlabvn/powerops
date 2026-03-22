// Monaco editor wrapper for KB lab HCL editing

import { useCallback, useRef } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'

interface KBLabEditorProps {
  value: string
  onChange: (v: string) => void
  language?: string
}

export function KBLabEditor({ value, onChange, language = 'hcl' }: KBLabEditorProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const monacoRef = useRef<any>(null)

  const handleMount: OnMount = useCallback((_editor, monaco) => {
    monacoRef.current = monaco
    const langs = monaco.languages.getLanguages()
    if (!langs.find((l: { id: string }) => l.id === 'hcl')) {
      monaco.languages.register({ id: 'hcl', extensions: ['.tf', '.hcl'] })
      monaco.languages.setMonarchTokensProvider('hcl', {
        keywords: ['resource', 'variable', 'output', 'module', 'provider', 'terraform',
                   'locals', 'data', 'true', 'false', 'null'],
        tokenizer: {
          root: [
            [/#.*$/, 'comment'],
            [/"([^"\\]|\\.)*"/, 'string'],
            [/\b\d+(\.\d+)?\b/, 'number'],
            [/\b(true|false|null)\b/, 'keyword'],
            [/[{}[\]()]/, 'delimiter'],
            [/[a-zA-Z_]\w*/, { cases: { '@keywords': 'keyword', '@default': 'identifier' } }],
          ],
        },
      })
    }
  }, [])

  return (
    <div className="border border-zinc-700 rounded-md overflow-hidden" style={{ height: 400 }}>
      <Editor
        height="400px"
        language={language}
        value={value}
        theme="vs-dark"
        options={{
          fontSize: 13,
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          wordWrap: 'on',
          tabSize: 2,
          automaticLayout: true,
          lineNumbers: 'on',
          scrollbar: { verticalScrollbarSize: 6, horizontalScrollbarSize: 6 },
        }}
        onChange={(v) => onChange(v ?? '')}
        onMount={handleMount}
      />
    </div>
  )
}
