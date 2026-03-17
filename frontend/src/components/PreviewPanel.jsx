import { useState } from 'react'
import { Eye, Code, Copy, Download, Save, Check } from 'lucide-react'
import toast from 'react-hot-toast'

export default function PreviewPanel({ html, loading, onSave, isSaved }) {
  const [tab, setTab] = useState('preview')
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    if (!html) return
    navigator.clipboard.writeText(html)
    setCopied(true)
    toast.success('Copied to clipboard')
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownload = () => {
    if (!html) return
    const blob = new Blob([html], { type: 'text/html' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'dashboard.html'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="flex flex-col h-full bg-gray-950">
      {/* Tab bar */}
      <div className="flex items-center px-4 border-b border-gray-800 gap-1 h-12 shrink-0">
        <TabBtn active={tab === 'preview'} onClick={() => setTab('preview')} icon={<Eye size={14} />} label="Preview" />
        <TabBtn active={tab === 'code'} onClick={() => setTab('code')} icon={<Code size={14} />} label="Code" />

        {html && (
          <div className="ml-auto flex items-center gap-2">
            {tab === 'code' && (
              <>
                <button onClick={handleCopy} className="btn-ghost gap-1.5">
                  {copied ? <Check size={14} className="text-green-400" /> : <Copy size={14} />}
                  <span>{copied ? 'Copied' : 'Copy'}</span>
                </button>
                <button onClick={handleDownload} className="btn-ghost gap-1.5">
                  <Download size={14} />
                  <span>Download</span>
                </button>
              </>
            )}
            <button
              onClick={onSave}
              disabled={isSaved}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                isSaved
                  ? 'bg-green-500/20 text-green-400 cursor-default'
                  : 'bg-brand-500 hover:bg-brand-600 text-white'
              }`}
            >
              {isSaved ? <Check size={13} /> : <Save size={13} />}
              {isSaved ? 'Saved' : 'Save Dashboard'}
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden relative">
        {loading && (
          <div className="absolute inset-0 bg-gray-950/80 z-10 flex flex-col items-center justify-center gap-3">
            <div className="w-8 h-8 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
            <p className="text-sm text-gray-400">Generating dashboard…</p>
          </div>
        )}

        {!html && !loading && (
          <div className="flex items-center justify-center h-full text-gray-600 select-none">
            <div className="text-center">
              <Eye size={40} className="mx-auto mb-3 opacity-20" />
              <p className="text-sm">Dashboard preview will appear here</p>
            </div>
          </div>
        )}

        {html && tab === 'preview' && (
          <iframe
            srcDoc={html}
            title="Dashboard Preview"
            sandbox="allow-scripts"
            className="w-full h-full border-0"
          />
        )}

        {html && tab === 'code' && (
          <pre className="w-full h-full overflow-auto p-4 text-xs text-gray-300 font-mono leading-relaxed scrollbar-thin bg-gray-900">
            {html}
          </pre>
        )}
      </div>
    </div>
  )
}

function TabBtn({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
        active ? 'bg-gray-800 text-gray-100' : 'text-gray-500 hover:text-gray-300'
      }`}
    >
      {icon}
      {label}
    </button>
  )
}
