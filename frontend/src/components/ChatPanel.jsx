import { useState, useRef, useEffect } from 'react'
import { Send, Upload, Paperclip, Zap, X, ChevronRight, Users, FolderKanban, Globe, User } from 'lucide-react'
import toast from 'react-hot-toast'
import { fetchAsanaData, fetchAsanaMembers, fetchAsanaProjects } from '../api'

export default function ChatPanel({ messages, onSend, loading, hasHtml, activeJsonName, onClearJson }) {
  const [input, setInput] = useState('')
  const [jsonData, setJsonData] = useState(null)
  const [jsonFileName, setJsonFileName] = useState('')
  const [asanaScope, setAsanaScope] = useState(null)      // { type, gid, name }
  const [scopeModalOpen, setScopeModalOpen] = useState(false)
  const fileRef = useRef()
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    const text = input.trim()
    if (!text && !jsonData) return
    onSend(text, jsonData, asanaScope)
    setInput('')
    setJsonData(null)
    setJsonFileName('')
    setAsanaScope(null)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target.result)
        setJsonData(parsed)
        setJsonFileName(file.name)
        setAsanaScope(null)
      } catch {
        toast.error('Invalid JSON file')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleScopeSelect = async (type, gid, name) => {
    setScopeModalOpen(false)
    try {
      toast.loading(`Fetching data for "${name}"…`, { id: 'asana-scope' })
      const data = await fetchAsanaData({ scope_type: type, scope_gid: gid })
      setJsonData(data)
      setJsonFileName(`asana: ${name}`)
      setAsanaScope({ type, gid, name })
      toast.success(`Loaded: ${name}`, { id: 'asana-scope' })
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Failed to fetch Asana data'
      toast.error(detail, { id: 'asana-scope' })
    }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-800 flex items-center gap-2">
        <Zap size={16} className="text-brand-500" />
        <span className="font-semibold text-sm">AI Dashboard Builder</span>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 select-none gap-3">
            <div className="w-12 h-12 rounded-2xl bg-brand-500/20 flex items-center justify-center">
              <Zap size={24} className="text-brand-500" />
            </div>
            <div>
              <p className="font-medium text-gray-300">Start building a dashboard</p>
              <p className="text-sm mt-1">Describe your data or paste JSON and I'll generate a beautiful dashboard.</p>
            </div>
            <div className="text-xs text-gray-600 space-y-1 max-w-xs">
              <p>• "Create a sales dashboard with monthly revenue and top products"</p>
              <p>• Paste or upload a JSON file along with your description</p>
              <p>• Use "Asana" to pick a project or team member dashboard</p>
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <ChatBubble key={i} message={msg} />
        ))}
        {loading && (
          <div className="flex items-start gap-2">
            <div className="w-7 h-7 rounded-full bg-brand-500 flex items-center justify-center text-xs font-bold shrink-0">AI</div>
            <div className="bg-gray-800 rounded-2xl rounded-tl-sm px-4 py-3">
              <TypingDots />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* New JSON / Asana scope badge — for this message */}
      {jsonFileName && (
        <div className="mx-4 mb-1 flex items-center gap-2 bg-brand-500/10 border border-brand-500/30 rounded-lg px-3 py-1.5 text-xs text-brand-500">
          <Paperclip size={12} />
          <span className="truncate flex-1">{jsonFileName}</span>
          <button onClick={() => { setJsonData(null); setJsonFileName(''); setAsanaScope(null) }} className="hover:text-red-400">✕</button>
        </div>
      )}

      {/* Persistent active JSON badge */}
      {!jsonFileName && activeJsonName && (
        <div className="mx-4 mb-1 flex items-center gap-2 bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-400">
          <Paperclip size={12} className="shrink-0" />
          <span className="truncate flex-1">{activeJsonName}</span>
          <button onClick={onClearJson} title="Clear JSON" className="hover:text-red-400 shrink-0">✕</button>
        </div>
      )}

      {/* Input area */}
      <div className="p-3 border-t border-gray-800 space-y-2">
        <div className="flex gap-2">
          <button
            onClick={() => fileRef.current?.click()}
            title="Upload JSON"
            className="shrink-0 w-9 h-9 rounded-lg bg-gray-800 hover:bg-gray-700 flex items-center justify-center text-gray-400 hover:text-gray-100 transition-colors"
          >
            <Upload size={15} />
          </button>
          <input ref={fileRef} type="file" accept=".json" className="hidden" onChange={handleFile} />

          <button
            onClick={() => setScopeModalOpen(true)}
            title="Import from Asana"
            className="shrink-0 px-2 h-9 rounded-lg bg-gray-800 hover:bg-gray-700 flex items-center gap-1.5 text-gray-400 hover:text-gray-100 transition-colors text-xs font-medium"
          >
            <span className="text-amber-400 font-bold">A</span> Asana
          </button>

          <textarea
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={handleKey}
            placeholder={hasHtml ? "Refine: 'change to dark theme', 'add a pie chart'…" : "Describe your dashboard or paste JSON…"}
            rows={1}
            className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm resize-none leading-5 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-gray-500 scrollbar-thin"
            style={{ maxHeight: '120px', overflowY: 'auto' }}
            onInput={e => {
              e.target.style.height = 'auto'
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
            }}
          />

          <button
            onClick={handleSend}
            disabled={loading || (!input.trim() && !jsonData)}
            className="shrink-0 w-9 h-9 rounded-lg bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          >
            <Send size={15} />
          </button>
        </div>
      </div>

      {/* Asana Scope Modal */}
      {scopeModalOpen && (
        <AsanaScopeModal
          onClose={() => setScopeModalOpen(false)}
          onSelect={handleScopeSelect}
        />
      )}
    </div>
  )
}

// ── Asana Scope Modal ─────────────────────────────────────────────────────────

function AsanaScopeModal({ onClose, onSelect }) {
  const [projects, setProjects] = useState([])
  const [members, setMembers] = useState([])
  const [loadStatus, setLoadStatus] = useState('loading') // loading | done | error
  const [tab, setTab] = useState('projects') // 'projects' | 'members'

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const [proj, mem] = await Promise.all([fetchAsanaProjects(), fetchAsanaMembers()])
        if (!cancelled) {
          setProjects(proj)
          setMembers(mem)
          setLoadStatus('done')
        }
      } catch (err) {
        if (!cancelled) setLoadStatus('error')
      }
    })()
    return () => { cancelled = true }
  }, [])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-sm shadow-2xl flex flex-col max-h-[80vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
          <div className="flex items-center gap-2">
            <span className="text-amber-400 font-bold text-base">A</span>
            <span className="font-semibold text-sm">Import from Asana</span>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-100 transition-colors">
            <X size={16} />
          </button>
        </div>

        {/* Quick actions */}
        <div className="px-4 pt-3 pb-2 flex gap-2">
          <QuickBtn
            icon={<Globe size={13} />}
            label="All Workspace"
            onClick={() => onSelect(null, null, 'All Workspace')}
          />
          <QuickBtn
            icon={<User size={13} />}
            label="My Tasks"
            onClick={() => onSelect('user', 'me', 'My Tasks')}
          />
        </div>

        {/* Tabs */}
        <div className="flex px-4 gap-1 border-b border-gray-800 pb-0">
          <TabBtn active={tab === 'projects'} onClick={() => setTab('projects')} icon={<FolderKanban size={12} />} label="Projects" />
          <TabBtn active={tab === 'members'} onClick={() => setTab('members')} icon={<Users size={12} />} label="Members" />
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto scrollbar-thin p-2">
          {loadStatus === 'loading' && (
            <div className="flex items-center justify-center py-10 gap-2 text-gray-500 text-sm">
              <div className="w-4 h-4 border-2 border-brand-500 border-t-transparent rounded-full animate-spin" />
              Loading workspace…
            </div>
          )}
          {loadStatus === 'error' && (
            <div className="text-center py-8 text-sm text-red-400">
              Failed to load. Check Asana connection in Settings.
            </div>
          )}
          {loadStatus === 'done' && tab === 'projects' && (
            projects.length === 0
              ? <p className="text-center py-8 text-sm text-gray-600">No projects found.</p>
              : projects.map(p => (
                  <ScopeRow
                    key={p.gid}
                    icon={<FolderKanban size={13} className="text-blue-400" />}
                    label={p.name}
                    onClick={() => onSelect('project', p.gid, p.name)}
                  />
                ))
          )}
          {loadStatus === 'done' && tab === 'members' && (
            members.length === 0
              ? <p className="text-center py-8 text-sm text-gray-600">No members found.</p>
              : members.map(m => (
                  <ScopeRow
                    key={m.gid}
                    icon={<User size={13} className="text-purple-400" />}
                    label={m.name}
                    sub={m.email}
                    onClick={() => onSelect('user', m.gid, m.name)}
                  />
                ))
          )}
        </div>
      </div>
    </div>
  )
}

function QuickBtn({ icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-medium text-gray-300 hover:text-white transition-colors"
    >
      {icon}{label}
    </button>
  )
}

function ScopeRow({ icon, label, sub, onClick }) {
  return (
    <button
      onClick={onClick}
      className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg hover:bg-gray-800 text-left transition-colors group"
    >
      <span className="shrink-0">{icon}</span>
      <span className="flex-1 min-w-0">
        <span className="block text-sm text-gray-200 truncate">{label}</span>
        {sub && <span className="block text-xs text-gray-500 truncate">{sub}</span>}
      </span>
      <ChevronRight size={13} className="text-gray-600 group-hover:text-gray-400 shrink-0" />
    </button>
  )
}

function TabBtn({ active, onClick, icon, label }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
        active
          ? 'border-brand-500 text-gray-100'
          : 'border-transparent text-gray-500 hover:text-gray-300'
      }`}
    >
      {icon}{label}
    </button>
  )
}

function ChatBubble({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`flex items-start gap-2 ${isUser ? 'flex-row-reverse' : ''}`}>
      <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0 ${isUser ? 'bg-gray-600' : 'bg-brand-500'}`}>
        {isUser ? 'U' : 'AI'}
      </div>
      <div className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
        isUser ? 'bg-brand-500 text-white rounded-tr-sm' : 'bg-gray-800 text-gray-100 rounded-tl-sm'
      }`}>
        {message.content}
      </div>
    </div>
  )
}

function TypingDots() {
  return (
    <div className="flex gap-1 items-center h-4">
      {[0, 1, 2].map(i => (
        <span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-gray-400 animate-bounce"
          style={{ animationDelay: `${i * 0.15}s` }}
        />
      ))}
    </div>
  )
}
