import { NavLink } from 'react-router-dom'
import { LayoutGrid, Settings, ChevronRight, X } from 'lucide-react'
import { cn } from '../lib/utils'
import { useAppStore } from '../stores/useAppStore'

// Everything else (Projects, Files, Wiki, Graph, Journal, CRM, Vault Health,
// Chakravyuha) still exists and still works — just reached through the chat
// now, not a side menu. Home is the task board.
const NAV_SECTIONS = [
  {
    label: 'Core',
    items: [
      { to: '/', icon: LayoutGrid, label: 'Board' },
    ],
  },
]

function BrandMark() {
  return (
    <div className="grid grid-cols-3 gap-[3px] shrink-0" aria-hidden>
      {Array(9).fill(0).map((_, i) => (
        <div
          key={i}
          className={cn(
            'w-[5px] h-[5px] rounded-full',
            [0, 2, 4, 6, 8].includes(i) ? 'bg-lattice-400' : 'bg-lattice-800'
          )}
        />
      ))}
    </div>
  )
}

function NavItem({ to, icon: Icon, label, open, onNavigate }) {
  return (
    <NavLink
      to={to}
      end={to === '/'}
      title={!open ? label : undefined}
      onClick={onNavigate}
      className={({ isActive }) =>
        open
          ? cn(
              'flex items-center gap-2.5 py-2.5 lg:py-[7px] pr-3 text-[13px] w-full transition-colors duration-100',
              isActive
                ? 'border-l-2 border-lattice-500 pl-[10px] text-dark-text bg-lattice-500/5'
                : 'border-l-2 border-transparent pl-[10px] text-dark-subtle hover:text-dark-text hover:bg-white/[0.02]'
            )
          : cn(
              'flex items-center justify-center w-full py-[7px] transition-colors duration-100 rounded-sm',
              isActive ? 'text-lattice-400' : 'text-dark-muted hover:text-dark-subtle hover:bg-white/[0.02]'
            )
      }
    >
      {({ isActive }) => (
        <>
          <Icon size={15} className={cn('shrink-0', isActive && open ? 'text-lattice-400' : '')} />
          {open && <span className="truncate">{label}</span>}
        </>
      )}
    </NavLink>
  )
}

export default function Sidebar() {
  const { sidebarOpen, toggleSidebar, mobileNavOpen, closeMobileNav } = useAppStore()

  // Mobile: off-canvas drawer, full width, backdrop-dismissed — no icon-rail state.
  // Desktop (lg+): existing push layout that collapses to an icon rail.
  const open = mobileNavOpen || sidebarOpen

  return (
    <>
      {/* Mobile backdrop */}
      {mobileNavOpen && (
        <div
          onClick={closeMobileNav}
          className="fixed inset-0 z-30 bg-black/60 lg:hidden"
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'flex flex-col bg-dark-surface border-r border-dark-border/50 shrink-0',
          'fixed inset-y-0 left-0 z-40 w-[240px] transform transition-transform duration-200',
          mobileNavOpen ? 'translate-x-0' : '-translate-x-full',
          'lg:static lg:translate-x-0 lg:transition-[width] lg:duration-200',
          sidebarOpen ? 'lg:w-[210px]' : 'lg:w-[48px]'
        )}
      >
        {/* Logo */}
        <div className={cn(
          'flex items-center h-11 px-3 border-b border-dark-border/50 shrink-0 justify-between',
          !open && 'lg:justify-center'
        )}>
          <div className={cn('flex items-center gap-2.5', !open && 'lg:justify-center')}>
            <BrandMark />
            {open && (
              <span className="font-semibold text-[13px] text-dark-text">Lattice</span>
            )}
          </div>
          {/* Desktop rail collapse toggle */}
          {sidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="hidden lg:block text-dark-muted hover:text-dark-subtle transition-colors p-0.5 rounded cursor-pointer"
              aria-label="Collapse sidebar"
            >
              <ChevronRight size={13} className="rotate-180" />
            </button>
          )}
          {/* Mobile drawer close */}
          <button
            onClick={closeMobileNav}
            className="lg:hidden text-dark-muted hover:text-dark-subtle transition-colors p-1 -mr-1 rounded cursor-pointer"
            aria-label="Close menu"
          >
            <X size={16} />
          </button>
        </div>

        {/* Nav sections */}
        <nav className="flex-1 overflow-y-auto py-2">
          {NAV_SECTIONS.map((section, si) => (
            <div key={section.label} className={cn(si > 0 && 'mt-2')}>
              {open && (
                <p className="px-3 pb-1 pt-0.5 text-[10px] font-semibold tracking-widest uppercase text-dark-muted/70">
                  {section.label}
                </p>
              )}
              {!open && si > 0 && (
                <div className="mx-2.5 mb-1.5 border-t border-dark-border/40 hidden lg:block" />
              )}
              {section.items.map((item) => (
                <NavItem key={item.to} {...item} open={open} onNavigate={closeMobileNav} />
              ))}
            </div>
          ))}
        </nav>

        {/* Settings + toggle */}
        <div className="border-t border-dark-border/50 py-1.5">
          <NavLink
            to="/settings"
            title={!open ? 'Settings' : undefined}
            onClick={closeMobileNav}
            className={({ isActive }) =>
              open
                ? cn(
                    'flex items-center gap-2.5 py-2.5 lg:py-[7px] pr-3 text-[13px] w-full transition-colors border-l-2',
                    isActive
                      ? 'border-lattice-500 pl-[10px] text-dark-text bg-lattice-500/5'
                      : 'border-transparent pl-[10px] text-dark-subtle hover:text-dark-text'
                  )
                : cn(
                    'flex justify-center w-full py-[7px] transition-colors',
                    isActive ? 'text-lattice-400' : 'text-dark-muted hover:text-dark-subtle'
                  )
            }
          >
            {({ isActive }) => (
              <>
                <Settings size={15} className={cn('shrink-0', !open && 'mx-auto', isActive && open ? 'text-lattice-400' : '')} />
                {open && <span>Settings</span>}
              </>
            )}
          </NavLink>

          {!sidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="hidden lg:flex w-full justify-center py-1.5 mt-0.5 text-dark-muted hover:text-dark-subtle transition-colors cursor-pointer"
              aria-label="Expand sidebar"
            >
              <ChevronRight size={13} />
            </button>
          )}
        </div>
      </aside>
    </>
  )
}
