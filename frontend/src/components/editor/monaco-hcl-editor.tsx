// Monaco Editor wrapper with HCL syntax highlighting and Ctrl+S save handler.
// Requires @monaco-editor/react to be installed.

import { useEffect, useRef, useCallback } from 'react'
import Editor, { type OnMount } from '@monaco-editor/react'

interface ValidationError {
  line?: number
  message: string
}

interface MonacoHclEditorProps {
  content: string
  language?: string
  onChange: (value: string) => void
  onSave?: (value: string) => void
  validationErrors?: ValidationError[]
  readOnly?: boolean
  hasUnsavedChanges?: boolean
}

export function MonacoHclEditor({
  content,
  language = 'hcl',
  onChange,
  onSave,
  validationErrors = [],
  readOnly = false,
  hasUnsavedChanges = false,
}: MonacoHclEditorProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const editorRef = useRef<any>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const monacoRef = useRef<any>(null)

  // Register HCL as a Monaco language on first mount
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const handleMount: OnMount = useCallback((editor: any, monaco: any) => {
    editorRef.current = editor
    monacoRef.current = monaco

    // Register HCL language if not already registered
    const langs = monaco.languages.getLanguages()
    if (!langs.find((l: { id: string }) => l.id === 'hcl')) {
      monaco.languages.register({ id: 'hcl', extensions: ['.tf', '.tfvars', '.hcl'] })
      monaco.languages.setMonarchTokensProvider('hcl', {
        keywords: ['resource', 'variable', 'output', 'module', 'provider', 'terraform',
                   'locals', 'data', 'for_each', 'count', 'depends_on', 'lifecycle',
                   'true', 'false', 'null'],
        tokenizer: {
          root: [
            [/#.*$/, 'comment'],
            [/"([^"\\]|\\.)*"/, 'string'],
            [/\b\d+(\.\d+)?\b/, 'number'],
            [/\b(true|false|null)\b/, 'keyword'],
            [/[{}[\]()]/, 'delimiter'],
            [/[a-zA-Z_]\w*/, {
              cases: {
                '@keywords': 'keyword',
                '@default': 'identifier',
              },
            }],
          ],
        },
      })
    }

    // Ctrl+S / Cmd+S → save handler
    editor.addCommand(
      monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS,
      () => {
        if (onSave) {
          const value = editor.getValue()
          onSave(value)
        }
      },
    )

    // Apply validation markers
    _applyMarkers(editor, monaco, validationErrors)
  }, [onSave, validationErrors])

  // Sync validation errors to Monaco markers when they change
  useEffect(() => {
    if (editorRef.current && monacoRef.current) {
      _applyMarkers(editorRef.current, monacoRef.current, validationErrors)
    }
  }, [validationErrors])

  return (
    <div className="flex flex-col h-full">
      {/* Unsaved indicator */}
      {hasUnsavedChanges && (
        <div className="flex items-center gap-2 px-3 py-1 bg-yellow-500/10 border-b border-yellow-500/30 text-yellow-400 text-xs">
          <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" />
          Unsaved changes — Ctrl+S to save
        </div>
      )}

      <div className="flex-1">
        <Editor
          height="100%"
          language={language === 'hcl' ? 'hcl' : language}
          value={content}
          theme="vs-dark"
          options={{
            readOnly,
            fontSize: 13,
            fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
            minimap: { enabled: false },
            scrollBeyondLastLine: false,
            wordWrap: 'on',
            tabSize: 2,
            insertSpaces: true,
            automaticLayout: true,
            lineNumbers: 'on',
            renderLineHighlight: 'all',
            scrollbar: { verticalScrollbarSize: 6, horizontalScrollbarSize: 6 },
          }}
          onChange={(value) => onChange(value ?? '')}
          onMount={handleMount}
        />
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function _applyMarkers(editor: any, monaco: any, errors: ValidationError[]) {
  const model = editor.getModel()
  if (!model) return
  const markers = errors.map(e => ({
    severity: monaco.MarkerSeverity.Error,
    startLineNumber: e.line ?? 1,
    startColumn: 1,
    endLineNumber: e.line ?? 1,
    endColumn: Number.MAX_SAFE_INTEGER,
    message: e.message,
  }))
  monaco.editor.setModelMarkers(model, 'hcl-validation', markers)
}
