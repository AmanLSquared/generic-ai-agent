import { useState } from 'react'
import toast from 'react-hot-toast'
import ChatPanel from '../components/ChatPanel'
import PreviewPanel from '../components/PreviewPanel'
import { generateDashboard, continueDashboard, saveDashboard } from '../api'

function extractSchema(jsonData) {
  if (!jsonData || typeof jsonData !== 'object') return {}
  // For schema, store top-level keys with example values (only primitives or first-item for arrays)
  const schema = {}
  for (const [key, value] of Object.entries(jsonData)) {
    if (Array.isArray(value)) {
      schema[key] = value[0] ?? []
    } else {
      schema[key] = value
    }
  }
  return schema
}

function autoName(prompt) {
  const clean = prompt.replace(/[^a-z0-9 ]/gi, '').trim()
  const words = clean.split(/\s+/).slice(0, 5)
  return words.join(' ') || 'Dashboard'
}

export default function Home() {
  const [messages, setMessages] = useState([])
  const [currentHtml, setCurrentHtml] = useState('')
  const [loading, setLoading] = useState(false)
  const [savedId, setSavedId] = useState(null)
  const [lastJsonData, setLastJsonData] = useState(null)
  const [lastJsonSchema, setLastJsonSchema] = useState(null)

  const isFirstMessage = messages.length === 0

  const handleSend = async (text, jsonData) => {
    const userContent = text || (jsonData ? 'Generate a dashboard from this data.' : '')
    if (!userContent && !jsonData) return

    const userMsg = { role: 'user', content: userContent }
    const newMessages = [...messages, userMsg]
    setMessages(newMessages)
    setLoading(true)
    setSavedId(null)

    // If new JSON is provided, store it; otherwise keep using the previously uploaded JSON
    const activeJson = jsonData ?? lastJsonData
    if (jsonData) {
      setLastJsonData(jsonData)
      setLastJsonSchema(extractSchema(jsonData))
    }

    try {
      let html
      if (isFirstMessage || !currentHtml) {
        const res = await generateDashboard(userContent, activeJson)
        html = res.html
      } else {
        const chatMessages = newMessages.map(m => ({ role: m.role, content: m.content }))
        // Pass activeJson so the AI keeps the current data in context for refinements
        const res = await continueDashboard(chatMessages, currentHtml, activeJson)
        html = res.html
      }
      setCurrentHtml(html)
      setMessages(prev => [...prev, { role: 'assistant', content: 'Dashboard updated! You can refine it or save it.' }])
    } catch (err) {
      const detail = err?.response?.data?.detail || err.message || 'Generation failed'
      toast.error(detail)
      setMessages(prev => [...prev, { role: 'assistant', content: `Error: ${detail}` }])
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!currentHtml) return
    const name = autoName(messages[0]?.content || 'Dashboard')
    const schema = lastJsonSchema || {}
    try {
      const saved = await saveDashboard({ name, html: currentHtml, json_schema: schema })
      setSavedId(saved.id)
      // Clear the persisted JSON after saving — start fresh if user wants a new dashboard
      setLastJsonData(null)
      setLastJsonSchema(null)
      toast.success(`Dashboard "${name}" saved!`)
    } catch {
      toast.error('Failed to save dashboard')
    }
  }

  return (
    <div className="flex h-full">
      {/* Chat panel — left */}
      <div className="w-96 shrink-0 border-r border-gray-800 flex flex-col">
        <ChatPanel
          messages={messages}
          onSend={handleSend}
          loading={loading}
          hasHtml={!!currentHtml}
          activeJsonName={lastJsonData ? '(using uploaded JSON)' : null}
          onClearJson={() => { setLastJsonData(null); setLastJsonSchema(null) }}
        />
      </div>

      {/* Preview panel — right */}
      <div className="flex-1 flex flex-col">
        <PreviewPanel
          html={currentHtml}
          loading={loading}
          onSave={handleSave}
          isSaved={!!savedId}
        />
      </div>
    </div>
  )
}
