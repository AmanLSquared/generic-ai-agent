import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// ── Generate ──────────────────────────────────────────────────────────────────
export const generateDashboard = (prompt, jsonData) =>
  api.post('/generate', { prompt, json_data: jsonData }).then(r => r.data)

export const continueDashboard = (messages, currentHtml, jsonData) =>
  api.post('/generate/continue', { messages, current_html: currentHtml, json_data: jsonData }).then(r => r.data)

// ── Dashboards ────────────────────────────────────────────────────────────────
export const listDashboards = () => api.get('/dashboards').then(r => r.data)

export const getDashboard = (id) => api.get(`/dashboards/${id}`).then(r => r.data)

export const saveDashboard = (payload) => api.post('/dashboards', payload).then(r => r.data)

export const updateDashboard = (id, payload) => api.put(`/dashboards/${id}`, payload).then(r => r.data)

export const deleteDashboard = (id) => api.delete(`/dashboards/${id}`).then(r => r.data)

export const injectData = (id, newData) =>
  api.post(`/dashboards/${id}/inject`, { new_data: newData }).then(r => r.data)

// ── Asana ─────────────────────────────────────────────────────────────────────
export const connectAsana = (pat) => api.post('/asana/connect', { pat }).then(r => r.data)

export const fetchAsanaData = (params = {}) => {
  const qs = new URLSearchParams()
  if (params.scope_type) qs.set('scope_type', params.scope_type)
  if (params.scope_gid) qs.set('scope_gid', params.scope_gid)
  const query = qs.toString()
  return api.get(`/asana/data${query ? '?' + query : ''}`).then(r => r.data)
}

export const fetchAsanaMembers = () => api.get('/asana/members').then(r => r.data.members)

export const fetchAsanaProjects = () => api.get('/asana/projects').then(r => r.data.projects)

// ── Settings ──────────────────────────────────────────────────────────────────
export const getSettings = () => api.get('/settings').then(r => r.data)

export const upsertSetting = (key, value) => api.put(`/settings/${key}`, { value }).then(r => r.data)

export const testOpenAI = () => api.post('/settings/test-openai').then(r => r.data)

export const clearHistory = () => api.delete('/settings/history').then(r => r.data)
