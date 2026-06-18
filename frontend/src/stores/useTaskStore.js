import { create } from 'zustand'
import { api } from '../lib/api'

export const BUCKETS = ['inbox', 'daily', 'weekly', 'long-term', 'someday']

export const useTaskStore = create((set, get) => ({
  tasks: [],
  stats: null,
  loading: false,
  error: null,

  fetch: async (params) => {
    set({ loading: true, error: null })
    try {
      const tasks = await api.tasks(params)
      set({ tasks, loading: false })
    } catch (e) {
      set({ error: e.message, loading: false })
    }
  },

  fetchStats: async () => {
    try {
      const stats = await api.taskStats()
      set({ stats })
    } catch {}
  },

  create: async (data) => {
    const task = await api.taskCreate(data)
    set((s) => ({ tasks: [task, ...s.tasks] }))
    return task
  },

  update: async (id, data) => {
    const task = await api.taskUpdate(id, data)
    set((s) => ({ tasks: s.tasks.map((t) => (t.id === id ? task : t)) }))
    return task
  },

  complete: async (id) => {
    await api.taskComplete(id)
    set((s) => ({
      tasks: s.tasks.map((t) =>
        t.id === id ? { ...t, status: 'done', completed_at: new Date().toISOString() } : t
      ),
    }))
  },

  remove: async (id) => {
    await api.taskDelete(id)
    set((s) => ({ tasks: s.tasks.filter((t) => t.id !== id) }))
  },

  byBucket: () => {
    const { tasks } = get()
    const buckets = {}
    BUCKETS.forEach((b) => (buckets[b] = []))
    tasks.forEach((t) => {
      if (t.status !== 'done' && buckets[t.bucket] !== undefined) {
        buckets[t.bucket].push(t)
      }
    })
    return buckets
  },
}))
