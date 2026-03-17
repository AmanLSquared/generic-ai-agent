import { useState, useEffect } from 'react'
import { Trash2, Eye, RefreshCw, Copy, Check, Upload } from 'lucide-react'
import toast from 'react-hot-toast'
import { listDashboards, deleteDashboard, injectData, fetchAsanaData } from '../api'

export default function HistoryPanel({ onOpen }) {
  const [dashboards, setDashboards] = useState([])
  const [search, setSearch] = useState('')
  const [injectModal, setInjectModal] = useState(null) // { dashboard }
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      const data = await listDashboards()
      setDashboards(data)
    } catch {
      toast.error('Failed to load dashboards')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleDelete = async (id) => {
    if (!confirm('Delete this dashboard?')) return
    try {
      await deleteDashboard(id)
      setDashboards(prev => prev.filter(d => d.id !== id))
      toast.success('Deleted')
    } catch {
      toast.error('Failed to delete')
    }
  }

  const filtered = dashboards.filter(d =>
    d.name.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-semibold">Saved Dashboards</h1>
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="Search…"
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-1.5 text-sm w-48 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-gray-500"
        />
      </div>

      {loading ? (
        <div className="flex-1 flex items-center justify-center text-gray-500">Loading…</div>
      ) : filtered.length === 0 ? (
        <div className="flex-1 flex items-center justify-center text-gray-600 text-sm">No saved dashboards yet.</div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4 overflow-y-auto scrollbar-thin">
          {filtered.map(d => (
            <DashboardCard
              key={d.id}
              dashboard={d}
              onOpen={onOpen}
              onDelete={() => handleDelete(d.id)}
              onUpdateData={() => setInjectModal({ dashboard: d })}
            />
          ))}
        </div>
      )}

      {injectModal && (
        <InjectModal
          dashboard={injectModal.dashboard}
          onClose={() => setInjectModal(null)}
          onSuccess={(updated) => {
            setDashboards(prev => prev.map(d => d.id === updated.id ? updated : d))
            setInjectModal(null)
            toast.success('Data updated successfully')
          }}
        />
      )}
    </div>
  )
}

function DashboardCard({ dashboard, onOpen, onDelete, onUpdateData }) {
  const [copied, setCopied] = useState(false)

  const handleCopyEmbed = () => {
    navigator.clipboard.writeText(dashboard.embed_code || '')
    setCopied(true)
    toast.success('Embed code copied')
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden hover:border-gray-700 transition-colors">
      {/* Mini preview */}
      <div className="h-36 bg-gray-950 overflow-hidden relative">
        <iframe
          srcDoc={dashboard.html}
          title={dashboard.name}
          sandbox="allow-scripts"
          className="w-full border-0 pointer-events-none origin-top-left"
          style={{ transform: 'scale(0.35)', width: '285%', height: '285%' }}
        />
      </div>

      <div className="p-3">
        <p className="font-medium text-sm truncate" title={dashboard.name}>{dashboard.name}</p>
        <p className="text-xs text-gray-500 mt-0.5">
          {new Date(dashboard.updated_at).toLocaleDateString()}
        </p>

        <div className="flex gap-1 mt-3 flex-wrap">
          <ActionBtn icon={<Eye size={12} />} label="Open" onClick={() => onOpen(dashboard)} />
          <ActionBtn icon={<RefreshCw size={12} />} label="Update Data" onClick={onUpdateData} />
          <ActionBtn
            icon={copied ? <Check size={12} /> : <Copy size={12} />}
            label="Embed"
            onClick={handleCopyEmbed}
          />
          <ActionBtn icon={<Trash2 size={12} />} label="Delete" onClick={onDelete} danger />
        </div>
      </div>
    </div>
  )
}

function ActionBtn({ icon, label, onClick, danger }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1 px-2 py-1 rounded text-xs transition-colors ${
        danger
          ? 'text-red-400 hover:bg-red-400/10'
          : 'text-gray-400 hover:bg-gray-800 hover:text-gray-100'
      }`}
    >
      {icon} {label}
    </button>
  )
}

// ── Inject Modal ──────────────────────────────────────────────────────────────

function InjectModal({ dashboard, onClose, onSuccess }) {
  const [step, setStep] = useState(1)
  const [newData, setNewData] = useState(null)
  const [fileName, setFileName] = useState('')
  const [mismatch, setMismatch] = useState(null)
  const [injecting, setInjecting] = useState(false)

  const schema = dashboard.json_schema
  const schemaKeys = Object.keys(schema)

  const handleFile = (e) => {
    const file = e.target.files[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (ev) => {
      try {
        const parsed = JSON.parse(ev.target.result)
        setNewData(parsed)
        setFileName(file.name)
        analyzeKeys(parsed)
        setStep(2)
      } catch {
        toast.error('Invalid JSON file')
      }
    }
    reader.readAsText(file)
    e.target.value = ''
  }

  const handleAsanaRefetch = async () => {
    try {
      toast.loading('Fetching from Asana…', { id: 'ainject' })
      const data = await fetchAsanaData()
      toast.success('Fetched!', { id: 'ainject' })
      setNewData(data)
      setFileName('asana-data.json')
      analyzeKeys(data)
      setStep(2)
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to fetch', { id: 'ainject' })
    }
  }

  const analyzeKeys = (data) => {
    const newKeys = new Set(Object.keys(data))
    const savedKeys = new Set(schemaKeys)
    const missing = [...savedKeys].filter(k => !newKeys.has(k))
    const extra = [...newKeys].filter(k => !savedKeys.has(k))
    if (missing.length || extra.length) {
      setMismatch({ missing, extra })
    } else {
      setMismatch(null)
    }
  }

  const handleInject = async () => {
    if (!newData) return
    // Block if >30% mismatch
    const missingCount = mismatch ? mismatch.missing.length : 0
    if (schemaKeys.length > 0 && missingCount / schemaKeys.length > 0.30) {
      toast.error('Too many mismatched keys. Injection blocked.')
      return
    }
    setInjecting(true)
    try {
      const updated = await injectData(dashboard.id, newData)
      onSuccess(updated)
    } catch (err) {
      const detail = err?.response?.data?.detail
      if (typeof detail === 'object') {
        toast.error(detail.message || 'Injection failed')
      } else {
        toast.error(detail || 'Injection failed')
      }
    } finally {
      setInjecting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-lg shadow-2xl">
        <div className="p-5 border-b border-gray-800 flex items-center justify-between">
          <h2 className="font-semibold">Update Data — {dashboard.name}</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-100">✕</button>
        </div>

        <div className="p-5 space-y-4">
          {/* Step 1: Show schema */}
          <div>
            <p className="text-xs text-gray-400 uppercase tracking-wider mb-2">Current Schema</p>
            <div className="bg-gray-800 rounded-lg p-3 text-xs font-mono text-gray-300 max-h-32 overflow-y-auto scrollbar-thin">
              {schemaKeys.map(k => (
                <div key={k} className="flex gap-2">
                  <span className="text-brand-500">{k}</span>
                  <span className="text-gray-500">: {JSON.stringify(schema[k])?.slice(0, 60)}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Step 2: Upload */}
          {step === 1 && (
            <div className="flex flex-col gap-3">
              <p className="text-sm text-gray-300">Upload new JSON data (same structure):</p>
              <label className="flex items-center justify-center gap-2 border-2 border-dashed border-gray-700 rounded-lg py-6 cursor-pointer hover:border-brand-500 transition-colors text-gray-400 hover:text-gray-200">
                <Upload size={16} />
                <span className="text-sm">Click to upload JSON</span>
                <input type="file" accept=".json" className="hidden" onChange={handleFile} />
              </label>
              {dashboard.asana_workspace_id && (
                <button onClick={handleAsanaRefetch} className="btn-secondary text-sm">
                  Re-fetch from Asana
                </button>
              )}
            </div>
          )}

          {/* Step 3: Confirm mismatch */}
          {step === 2 && mismatch && (
            <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-3 text-sm space-y-1">
              <p className="font-medium text-amber-400">Key mismatch detected</p>
              {mismatch.missing.length > 0 && (
                <p className="text-gray-300">Missing: <span className="text-red-400">{mismatch.missing.join(', ')}</span></p>
              )}
              {mismatch.extra.length > 0 && (
                <p className="text-gray-300">Extra: <span className="text-yellow-400">{mismatch.extra.join(', ')}</span></p>
              )}
            </div>
          )}

          {step === 2 && (
            <p className="text-xs text-gray-500">
              File: <span className="text-gray-300">{fileName}</span>
              {' · '}
              {Object.keys(newData || {}).length} keys
            </p>
          )}
        </div>

        <div className="p-5 border-t border-gray-800 flex justify-end gap-2">
          <button onClick={onClose} className="btn-ghost">Cancel</button>
          {step === 1 && (
            <label className="btn-primary cursor-pointer">
              Select JSON File
              <input type="file" accept=".json" className="hidden" onChange={handleFile} />
            </label>
          )}
          {step === 2 && (
            <button
              onClick={handleInject}
              disabled={injecting}
              className="btn-primary disabled:opacity-50"
            >
              {injecting ? 'Injecting…' : 'Inject Data'}
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
