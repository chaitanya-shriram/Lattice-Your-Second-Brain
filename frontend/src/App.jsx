import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import StatusBar from './components/StatusBar'
import ToastContainer from './components/Toast'
import Dashboard from './pages/Dashboard'
import Tasks from './pages/Tasks'
import BrainDump from './pages/BrainDump'
import Files from './pages/Files'
import Wiki from './pages/Wiki'
import Graph from './pages/Graph'
import Settings from './pages/Settings'
import Journal from './pages/Journal'
import CRM from './pages/CRM'
import XP from './pages/XP'
import Ask from './pages/Ask'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-dark-bg">
        <Sidebar />

        {/* Main content */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Top bar */}
          <header className="flex items-center justify-end px-4 py-2 border-b border-dark-border bg-dark-surface/60 shrink-0">
            <StatusBar />
          </header>

          {/* Page content */}
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/ask" element={<Ask />} />
              <Route path="/tasks" element={<Tasks />} />
              <Route path="/dump" element={<BrainDump />} />
              <Route path="/files" element={<Files />} />
              <Route path="/wiki" element={<Wiki />} />
              <Route path="/graph" element={<Graph />} />
              <Route path="/journal" element={<Journal />} />
              <Route path="/crm" element={<CRM />} />
              <Route path="/xp" element={<XP />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </div>

      <ToastContainer />
    </BrowserRouter>
  )
}
