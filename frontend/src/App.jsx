import { useState, useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Menu } from 'lucide-react'
import Sidebar from './components/Sidebar'
import StatusBar from './components/StatusBar'
import ToastContainer from './components/Toast'
import Tasks from './pages/Tasks'
import Projects from './pages/Projects'
import ProjectDetail from './pages/ProjectDetail'
import Files from './pages/Files'
import Wiki from './pages/Wiki'
import Graph from './pages/Graph'
import VaultHealth from './pages/VaultHealth'
import Settings from './pages/Settings'
import Journal from './pages/Journal'
import CRM from './pages/CRM'
import Chakravyuha from './pages/Chakravyuha'
import Setup from './pages/Setup'
import ChatBot from './components/projects/ChatBot'
import { api, auth } from './lib/api'
import { useAppStore } from './stores/useAppStore'

function Spinner() {
  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center">
      <div className="space-y-3 text-center">
        {/* Dot grid brand mark */}
        <div className="grid grid-cols-3 gap-[4px] mx-auto w-fit">
          {Array(9).fill(0).map((_, i) => (
            <div
              key={i}
              className={`w-2 h-2 rounded-full transition-opacity ${
                [0, 2, 4, 6, 8].includes(i) ? 'bg-lattice-400' : 'bg-lattice-900'
              }`}
              style={{ animationDelay: `${i * 80}ms` }}
            />
          ))}
        </div>
        <p className="text-dark-muted text-xs font-mono">lattice</p>
      </div>
    </div>
  )
}

function AuthPrompt({ onAuth }) {
  const [key, setKey] = useState('')
  const [error, setError] = useState('')
  const [checking, setChecking] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!key.trim()) return
    setChecking(true)
    setError('')
    auth.setKey(key.trim())
    try {
      await api.health()
      onAuth()
    } catch {
      auth.clearKey()
      setError('Key rejected — check LATTICE_API_KEY in .env')
    }
    setChecking(false)
  }

  return (
    <div className="min-h-screen bg-dark-bg flex items-center justify-center p-6">
      <div className="w-full max-w-[340px] space-y-6">
        {/* Brand */}
        <div className="space-y-1.5">
          <div className="grid grid-cols-3 gap-[4px] w-fit">
            {Array(9).fill(0).map((_, i) => (
              <div
                key={i}
                className={`w-2 h-2 rounded-full ${[0,2,4,6,8].includes(i) ? 'bg-lattice-400' : 'bg-lattice-900'}`}
              />
            ))}
          </div>
          <h1 className="text-lg font-semibold text-dark-text mt-3">Lattice</h1>
          <p className="text-sm text-dark-subtle">Enter your API key to continue</p>
        </div>

        {/* Form */}
        <form onSubmit={submit} className="space-y-3">
          <div className="space-y-1.5">
            <label className="text-xs text-dark-subtle font-medium">API Key</label>
            <input
              type="password"
              value={key}
              onChange={(e) => setKey(e.target.value)}
              placeholder="sk-••••••••••••••••"
              className="input-base font-mono"
              autoFocus
            />
          </div>
          {error && (
            <p className="text-xs text-red-400 flex items-center gap-1.5">
              <span className="w-1 h-1 rounded-full bg-red-400 shrink-0" />
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={!key.trim() || checking}
            className="btn-primary w-full justify-center py-2"
          >
            {checking ? 'Verifying…' : 'Unlock'}
          </button>
        </form>

        <p className="text-2xs text-dark-muted text-center">
          Set <code className="font-mono text-lattice-400">LATTICE_API_KEY</code> in your <code className="font-mono">.env</code>
        </p>
      </div>
    </div>
  )
}

export default function App() {
  const [setupChecked, setSetupChecked] = useState(false)
  const [needsSetup, setNeedsSetup]     = useState(false)
  const [needsAuth, setNeedsAuth]       = useState(false)
  const toggleMobileNav = useAppStore((s) => s.toggleMobileNav)

  const checkSetup = () => {
    api.setupStatus()
      .then((data) => {
        setNeedsSetup(data.needs_setup)
        setSetupChecked(true)
      })
      .catch((e) => {
        if (e.message === 'Unauthorized') {
          setNeedsAuth(true)
        }
        setSetupChecked(true)
      })
  }

  useEffect(() => {
    checkSetup()
    const handler = () => setNeedsAuth(true)
    window.addEventListener('lattice:unauthorized', handler)
    return () => window.removeEventListener('lattice:unauthorized', handler)
  }, [])

  if (!setupChecked) return <Spinner />
  if (needsAuth) return <AuthPrompt onAuth={() => { setNeedsAuth(false); checkSetup() }} />
  if (needsSetup) return <Setup onComplete={() => setNeedsSetup(false)} />

  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-dark-bg">
        <Sidebar />

        <div className="flex-1 flex flex-col overflow-hidden min-w-0">
          {/* Top bar */}
          <header className="h-10 flex items-center justify-between lg:justify-end px-4 border-b border-dark-border/60 bg-dark-surface/40 shrink-0">
            <button
              onClick={toggleMobileNav}
              className="lg:hidden text-dark-subtle hover:text-dark-text transition-colors p-1 -ml-1 cursor-pointer"
              aria-label="Open menu"
            >
              <Menu size={18} />
            </button>
            <StatusBar />
          </header>

          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/"        element={<Tasks />} />
              <Route path="/chakravyuha" element={<Chakravyuha />} />
              <Route path="/tasks"   element={<Tasks />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:id" element={<ProjectDetail />} />
              <Route path="/files"   element={<Files />} />
              <Route path="/wiki"    element={<Wiki />} />
              <Route path="/graph"   element={<Graph />} />
              <Route path="/vault-health" element={<VaultHealth />} />
              <Route path="/journal" element={<Journal />} />
              <Route path="/crm"     element={<CRM />} />
              <Route path="/settings"element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>
      <ChatBot />
      <ToastContainer />
    </BrowserRouter>
  )
}
