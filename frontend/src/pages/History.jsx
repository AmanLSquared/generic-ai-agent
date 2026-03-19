import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import HistoryPanel from '../components/HistoryPanel'
import PreviewPanel from '../components/PreviewPanel'

export default function History() {
  const [viewingDashboard, setViewingDashboard] = useState(null)
  const [liveHtml, setLiveHtml] = useState(null)
  const [liveLoading, setLiveLoading] = useState(false)
  const navigate = useNavigate()

  const handleOpen = async (dashboard) => {
    setViewingDashboard(dashboard)
    setLiveHtml(null)
    // If it has a Jinja2 template and a scope, fetch live rendered HTML
    if (dashboard.has_template && dashboard.asana_scope_type && dashboard.asana_scope_gid) {
      setLiveLoading(true)
      try {
        const param = dashboard.asana_scope_type === 'project'
          ? `project_id=${dashboard.asana_scope_gid}`
          : `user_id=${dashboard.asana_scope_gid}`
        const res = await fetch(`/render/${dashboard.id}?${param}`)
        if (res.ok) {
          setLiveHtml(await res.text())
        }
      } catch {
        toast.error('Could not fetch live data, showing saved preview')
      } finally {
        setLiveLoading(false)
      }
    }
  }

  if (viewingDashboard) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <button
            onClick={() => { setViewingDashboard(null); setLiveHtml(null) }}
            className="text-sm text-gray-400 hover:text-gray-100 transition-colors"
          >
            ← Back to History
          </button>
          <span className="text-sm font-medium">{viewingDashboard.name}</span>
          {viewingDashboard.has_template && viewingDashboard.asana_scope_gid && (
            <span className="text-xs text-green-400 ml-1">● Live Data</span>
          )}
          <span className="text-xs text-gray-500 ml-auto">Read-only view</span>
        </div>
        <div className="flex-1 overflow-hidden">
          <PreviewPanel
            html={liveHtml || viewingDashboard.html}
            loading={liveLoading}
            onSave={() => {}}
            isSaved={true}
          />
        </div>
      </div>
    )
  }

  return (
    <HistoryPanel onOpen={handleOpen} />
  )
}
