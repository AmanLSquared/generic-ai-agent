import { useState, useEffect } from 'react'
import { Eye, EyeOff, Check, X, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { upsertSetting, testOpenAI, connectAsana, clearHistory } from '../api'

export default function Settings() {
  const [openaiKey, setOpenaiKey] = useState('')
  const [asanaPat, setAsanaPat] = useState('')
  const [showOk, setShowOk] = useState(false)
  const [showAsana, setShowAsana] = useState(false)
  const [testingOai, setTestingOai] = useState(false)
  const [testingAsana, setTestingAsana] = useState(false)
  const [savingOai, setSavingOai] = useState(false)
  const [savingAsana, setSavingAsana] = useState(false)

  const handleSaveOpenAI = async () => {
    if (!openaiKey.trim()) return
    setSavingOai(true)
    try {
      await upsertSetting('openai_api_key', openaiKey.trim())
      toast.success('OpenAI API key saved')
      setOpenaiKey('')
    } catch {
      toast.error('Failed to save key')
    } finally {
      setSavingOai(false)
    }
  }

  const handleTestOpenAI = async () => {
    setTestingOai(true)
    try {
      await testOpenAI()
      toast.success('OpenAI key is valid ✓')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Invalid key')
    } finally {
      setTestingOai(false)
    }
  }

  const handleSaveAsana = async () => {
    if (!asanaPat.trim()) return
    setSavingAsana(true)
    try {
      const result = await connectAsana(asanaPat.trim())
      toast.success(`Connected as ${result.user?.name || 'Asana user'}`)
      setAsanaPat('')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Failed to connect')
    } finally {
      setSavingAsana(false)
    }
  }

  const handleTestAsana = async () => {
    setTestingAsana(true)
    try {
      // connectAsana tests and saves in one step — just test with current value
      if (!asanaPat.trim()) {
        toast('Enter a PAT first')
        return
      }
      await connectAsana(asanaPat.trim())
      toast.success('Asana PAT is valid ✓')
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Invalid PAT')
    } finally {
      setTestingAsana(false)
    }
  }

  const handleClearHistory = async () => {
    if (!confirm('Delete ALL saved dashboards? This cannot be undone.')) return
    try {
      await clearHistory()
      toast.success('History cleared')
    } catch {
      toast.error('Failed to clear history')
    }
  }

  return (
    <div className="max-w-xl mx-auto p-8">
      <h1 className="text-xl font-semibold mb-8">Settings</h1>

      <Section title="OpenAI">
        <p className="text-sm text-gray-400 mb-3">
          Your API key is stored locally in SQLite and never sent anywhere except OpenAI.
        </p>
        <div className="flex gap-2">
          <PasswordInput
            value={openaiKey}
            onChange={setOpenaiKey}
            placeholder="sk-…"
            show={showOk}
            onToggle={() => setShowOk(p => !p)}
          />
          <button onClick={handleTestOpenAI} disabled={testingOai} className="btn-ghost shrink-0">
            {testingOai ? <Loader size={14} className="animate-spin" /> : 'Test'}
          </button>
          <button onClick={handleSaveOpenAI} disabled={savingOai || !openaiKey.trim()} className="btn-primary shrink-0">
            {savingOai ? <Loader size={14} className="animate-spin" /> : 'Save'}
          </button>
        </div>
      </Section>

      <Section title="Asana">
        <p className="text-sm text-gray-400 mb-3">
          Enter your Personal Access Token from{' '}
          <span className="text-brand-500">app.asana.com → My Profile → Apps → Personal Access Tokens</span>.
          Stored encrypted.
        </p>
        <div className="flex gap-2">
          <PasswordInput
            value={asanaPat}
            onChange={setAsanaPat}
            placeholder="1/1234567890:…"
            show={showAsana}
            onToggle={() => setShowAsana(p => !p)}
          />
          <button onClick={handleTestAsana} disabled={testingAsana} className="btn-ghost shrink-0">
            {testingAsana ? <Loader size={14} className="animate-spin" /> : 'Test'}
          </button>
          <button onClick={handleSaveAsana} disabled={savingAsana || !asanaPat.trim()} className="btn-primary shrink-0">
            {savingAsana ? <Loader size={14} className="animate-spin" /> : 'Save'}
          </button>
        </div>
      </Section>

      <Section title="Data">
        <p className="text-sm text-gray-400 mb-3">
          Permanently delete all saved dashboards from local storage.
        </p>
        <button onClick={handleClearHistory} className="px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 rounded-lg text-sm transition-colors">
          Clear All History
        </button>
      </Section>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className="mb-8 pb-8 border-b border-gray-800 last:border-0">
      <h2 className="text-sm font-semibold text-gray-300 uppercase tracking-wider mb-4">{title}</h2>
      {children}
    </div>
  )
}

function PasswordInput({ value, onChange, placeholder, show, onToggle }) {
  return (
    <div className="relative flex-1">
      <input
        type={show ? 'text' : 'password'}
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm pr-9 focus:outline-none focus:ring-1 focus:ring-brand-500 placeholder:text-gray-500"
      />
      <button
        type="button"
        onClick={onToggle}
        className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200"
      >
        {show ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    </div>
  )
}
