import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import HistoryPanel from '../components/HistoryPanel'
import PreviewPanel from '../components/PreviewPanel'

export default function History() {
  const [viewingDashboard, setViewingDashboard] = useState(null)
  const navigate = useNavigate()

  if (viewingDashboard) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-800">
          <button
            onClick={() => setViewingDashboard(null)}
            className="text-sm text-gray-400 hover:text-gray-100 transition-colors"
          >
            ← Back to History
          </button>
          <span className="text-sm font-medium">{viewingDashboard.name}</span>
          <span className="text-xs text-gray-500 ml-auto">Read-only view</span>
        </div>
        <div className="flex-1 overflow-hidden">
          <PreviewPanel
            html={viewingDashboard.html}
            loading={false}
            onSave={() => {}}
            isSaved={true}
          />
        </div>
      </div>
    )
  }

  return (
    <HistoryPanel onOpen={(dashboard) => setViewingDashboard(dashboard)} />
  )
}
