const BASE = '/api'

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Health
  health: () => req('/health/'),

  // Brain dump
  dump: (text, source = 'web') =>
    req('/dump/', { method: 'POST', body: JSON.stringify({ text, source }) }),
  dumpHistory: () => req('/dump/history'),

  // Tasks
  tasks: (params = {}) => {
    const q = new URLSearchParams(params).toString()
    return req(`/tasks/${q ? '?' + q : ''}`)
  },
  taskCreate: (data) => req('/tasks/', { method: 'POST', body: JSON.stringify(data) }),
  taskGet: (id) => req(`/tasks/${id}`),
  taskUpdate: (id, data) =>
    req(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  taskDelete: (id) => req(`/tasks/${id}`, { method: 'DELETE' }),
  taskComplete: (id) => req(`/tasks/${id}/complete`, { method: 'POST' }),
  taskStats: () => req('/tasks/stats/summary'),

  // Files
  files: () => req('/files/'),
  fileUpload: (file) => {
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`${BASE}/files/upload`, { method: 'POST', body: fd }).then((r) => r.json())
  },

  // Wiki
  wiki: () => req('/wiki/'),
  wikiPage: (id) => req(`/wiki/${id}`),
  wikiSearch: (q) => req(`/wiki/search?q=${encodeURIComponent(q)}`),

  // Actions log
  actions: (limit = 50) => req(`/actions/?limit=${limit}`),

  // RAG / Ask
  ragQuery: (question, top_k = 5, use_graph = true) =>
    req('/graph/query', { method: 'POST', body: JSON.stringify({ question, top_k, use_graph }) }),
  graph: () => req('/graph/'),
  graphRebuild: () => req('/graph/rebuild', { method: 'POST' }),

  // Journal
  journalAdd: (text, reflect = true) =>
    req('/journal/', { method: 'POST', body: JSON.stringify({ text, reflect }) }),
  journalEntries: (limit = 10) => req(`/journal/entries?limit=${limit}`),
  journalToday: () => req('/journal/today'),

  // CRM
  crmList: (search = '') => req(`/crm/${search ? '?search=' + encodeURIComponent(search) : ''}`),
  crmUpsert: (data) => req('/crm/', { method: 'POST', body: JSON.stringify(data) }),

  // XP / Gamification
  xpStats: () => req('/xp/stats'),
  xpLog: (limit = 20) => req(`/xp/xp-log?limit=${limit}`),
  xpAchievements: () => req('/xp/achievements'),
  xpWeeklyReport: () => req('/xp/weekly-report'),
  xpAward: (action, context = '') =>
    req('/xp/award', { method: 'POST', body: JSON.stringify({ action, context }) }),
}
