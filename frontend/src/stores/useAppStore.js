import { create } from 'zustand'
import { api } from '../lib/api'

export const useAppStore = create((set) => ({
  health: null,
  dumpHistory: [],
  toasts: [],
  sidebarOpen: true,

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
    setTimeout(() => {
      set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) }))
    }, 4000)
  },

  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
}))
