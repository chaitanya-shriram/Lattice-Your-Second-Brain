const BASE = '/api'

const AUTH_KEY = 'lattice_api_key'

export const auth = {
  getKey: () => localStorage.getItem(AUTH_KEY) || '',
  setKey: (k) => localStorage.setItem(AUTH_KEY, k),
  clearKey: () => localStorage.removeItem(AUTH_KEY),
}

async function req(path, options = {}) {
  const key = auth.getKey()
  const res = await fetch(`${BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(key ? { Authorization: `Bearer ${key}` } : {}),
      ...options.headers,
    },
    ...options,
  })
  if (res.status === 401) {
    auth.clearKey()
    window.dispatchEvent(new Event('lattice:unauthorized'))
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export const api = {
  // Setup (no auth required)
  setupStatus: () => req('/setup/status'),
  setupBrowse: (title = 'Select folder') =>
    req('/setup/browse', { method: 'POST', body: JSON.stringify({ title }) }),
  setupSave: (root_path) =>
    req('/setup/save', { method: 'POST', body: JSON.stringify({ root_path }) }),
  setupRestart: () => req('/setup/restart', { method: 'POST' }),

  // Health
  health: () => req('/health/'),

  // Brain dump history — captures now come in through the chat, this just reads the log
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
    const key = auth.getKey()
    const fd = new FormData()
    fd.append('file', file)
    return fetch(`${BASE}/files/upload`, {
      method: 'POST',
      body: fd,
      headers: key ? { Authorization: `Bearer ${key}` } : {},
    }).then((r) => r.json())
  },

  // Wiki
  wiki: () => req('/wiki/'),
  wikiPage: (id) => req(`/wiki/${id}`),
  wikiSearch: (q) => req(`/wiki/search?q=${encodeURIComponent(q)}`),

  // Graph
  graph: () => req('/graph/'),
  graphRebuild: () => req('/graph/rebuild', { method: 'POST' }),

  // Journal
  journalAdd: (text, reflect = true) =>
    req('/journal/', { method: 'POST', body: JSON.stringify({ text, reflect }) }),
  journalEntries: (limit = 10) => req(`/journal/entries?limit=${limit}`),
  journalToday: () => req('/journal/today'),

  // Daily review
  dailyReviewGenerate: () => req('/daily-review/generate', { method: 'POST' }),

  // Vault health
  vaultHealthRun: () => req('/vault-health/run', { method: 'POST' }),

  // CRM
  crmList: (search = '') => req(`/crm/${search ? '?search=' + encodeURIComponent(search) : ''}`),
  crmUpsert: (data) => req('/crm/', { method: 'POST', body: JSON.stringify(data) }),

  // Backup
  backupCreate: () => {
    const key = auth.getKey()
    return fetch(`${BASE}/backup/create`, {
      method: 'POST',
      headers: key ? { Authorization: `Bearer ${key}` } : {},
    })
  },

  // LAN QR code — returns image URL (use directly in <img src>)
  qrUrl: () => `${BASE}/health/qr`,

  // Projects (task manager)
  projects: () => req('/projects/'),
  projectsHome: () => req('/projects/home'),
  projectsMyTasks: () => req('/projects/my-tasks'),
  projectCreate: (data) => req('/projects/', { method: 'POST', body: JSON.stringify(data) }),
  project: (id) => req(`/projects/${id}`),
  projectFull: (id) => req(`/projects/${id}/full`),
  projectUpdate: (id, data) => req(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  projectDelete: (id) => req(`/projects/${id}`, { method: 'DELETE' }),

  sectionCreate: (projectId, name) =>
    req(`/projects/${projectId}/sections`, { method: 'POST', body: JSON.stringify({ name }) }),
  sectionDelete: (id) => req(`/projects/sections/${id}`, { method: 'DELETE' }),

  projectTaskCreate: (projectId, data) =>
    req(`/projects/${projectId}/tasks`, { method: 'POST', body: JSON.stringify(data) }),
  projectTaskUpdate: (id, data) =>
    req(`/projects/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  projectTaskDelete: (id) => req(`/projects/tasks/${id}`, { method: 'DELETE' }),

  dependencyAdd: (taskId, dependsOnId) =>
    req(`/projects/tasks/${taskId}/dependencies`, { method: 'POST', body: JSON.stringify({ depends_on_id: dependsOnId }) }),
  dependencyRemove: (taskId, dependsOnId) =>
    req(`/projects/tasks/${taskId}/dependencies/${dependsOnId}`, { method: 'DELETE' }),

  statusUpdates: (projectId) => req(`/projects/${projectId}/updates`),
  statusUpdateCreate: (projectId, status, body) =>
    req(`/projects/${projectId}/updates`, { method: 'POST', body: JSON.stringify({ status, body }) }),
  statusUpdateDelete: (id) => req(`/projects/updates/${id}`, { method: 'DELETE' }),

  projectChat: (messages) =>
    req('/projects/chat', { method: 'POST', body: JSON.stringify({ messages }) }),

  // Intents (auto-planned commitments from Brain Dump)
  intents: () => req('/intents/'),
  intentsRunNow: () => req('/intents/run-now', { method: 'POST' }),
}
