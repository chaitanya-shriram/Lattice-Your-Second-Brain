import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  CheckSquare,
  FileText,
  BookOpen,
  GitBranch,
  Brain,
  Settings,
  ChevronLeft,
  Zap,
  BookMarked,
  Users,
  Trophy,
  MessageCircle,
} from 'lucide-react'
import { cn } from '../lib/utils'
import { useAppStore } from '../stores/useAppStore'

const NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/ask', icon: MessageCircle, label: 'Ask' },
  { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
  { to: '/dump', icon: Brain, label: 'Brain Dump' },
  { to: '/files', icon: FileText, label: 'Files' },
  { to: '/wiki', icon: BookOpen, label: 'Wiki' },
  { to: '/graph', icon: GitBranch, label: 'Graph' },
  { to: '/journal', icon: BookMarked, label: 'Journal' },
  { to: '/crm', icon: Users, label: 'People' },
  { to: '/xp', icon: Trophy, label: 'XP' },
]

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useAppStore()

  return (
    <aside
      className={cn(
        'flex flex-col bg-dark-surface border-r border-dark-border transition-all duration-200 shrink-0',
        sidebarOpen ? 'w-52' : 'w-14'
      )}
    >
      {/* Logo */}
      <div className="flex items-center justify-between px-3 py-4 border-b border-dark-border">
        <div className={cn('flex items-center gap-2', !sidebarOpen && 'justify-center w-full')}>
          <div className="w-7 h-7 rounded-lg bg-lattice-600 flex items-center justify-center shrink-0">
            <Zap size={14} className="text-white" />
          </div>
          {sidebarOpen && (
            <span className="font-bold text-sm text-lattice-300 tracking-wide">Lattice</span>
          )}
        </div>
        {sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="text-dark-subtle hover:text-dark-text transition-colors"
          >
            <ChevronLeft size={16} />
          </button>
        )}
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5">
        {NAV.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm transition-all duration-150',
                'hover:bg-dark-card hover:text-dark-text',
                isActive
                  ? 'bg-lattice-700/30 text-lattice-300 border border-lattice-700/40'
                  : 'text-dark-subtle',
                !sidebarOpen && 'justify-center'
              )
            }
          >
            <Icon size={16} className="shrink-0" />
            {sidebarOpen && <span>{label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom */}
      <div className="px-2 py-3 border-t border-dark-border">
        <NavLink
          to="/settings"
          className={cn(
            'flex items-center gap-2.5 px-2 py-2 rounded-lg text-sm text-dark-subtle',
            'hover:bg-dark-card hover:text-dark-text transition-all',
            !sidebarOpen && 'justify-center'
          )}
        >
          <Settings size={16} />
          {sidebarOpen && <span>Settings</span>}
        </NavLink>

        {!sidebarOpen && (
          <button
            onClick={toggleSidebar}
            className="w-full flex items-center justify-center p-2 mt-1 text-dark-subtle hover:text-dark-text"
          >
            <ChevronLeft size={14} className="rotate-180" />
          </button>
        )}
      </div>
    </aside>
  )
}
