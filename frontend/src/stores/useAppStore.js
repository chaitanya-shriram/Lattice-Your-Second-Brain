import { create } from 'zustand'
import { api } from '../lib/api'

export const useAppStore = create((set) => ({
  health: null,
  dumpHistory: [],
  toasts: [],
  sidebarOpen: true,
  mobileNavOpen: false,

  checkHealth: async () => {
    try {
      const h = await api.health()
      set({ health: h })
    } catch {
      set({ health: { status: 'offline', ollama: false } })
    }
  },

  fetchDumpHistory: async () => {
    try {
      const dumpHistory = await api.dumpHistory()
      set({ dumpHistory })
    } catch {}
  },

  addToast: (message, type = 'info') => {
    const id = Date.now()
    set((s) => ({ toasts: [...s.toasts, { id, message, type }] }))
  },

  removeToast: (id) => {
    set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
  },

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleMobileNav: () => set((s) => ({ mobileNavOpen: !s.mobileNavOpen })),
  closeMobileNav: () => set({ mobileNavOpen: false }),
}))
