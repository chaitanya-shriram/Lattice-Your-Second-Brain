import { create } from 'zustand'
import { api } from '../lib/api'

export const PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
export const STATUSES = ['on_track', 'at_risk', 'off_track', 'complete']
export const STATUS_LABELS = {
  on_track: 'On track',
  at_risk: 'At risk',
  off_track: 'Off track',
  complete: 'Complete',
}

export const useProjectStore = create((set, get) => ({
  projects: [],
  home: [],
  myTasks: [],
  current: null,       // { ...project, sections, tasks, updates }
  loading: false,
  error: null,

  fetchProjects: async () => {
    try {
      const projects = await api.projects()
      set({ projects })
    } catch (e) {
      set({ error: e.message })
    }
  },

  fetchHome: async () => {
    set({ loading: true, error: null })
    try {
      const home = await api.projectsHome()
      set({ home, loading: false })
    } catch (e) {
      set({ error: e.message, loading: false })
    }
  },

  fetchMyTasks: async () => {
    try {
      const myTasks = await api.projectsMyTasks()
      set({ myTasks })
    } catch (e) {
      set({ error: e.message })
    }
  },

  fetchCurrent: async (id) => {
    set({ loading: true, error: null })
    try {
      const current = await api.projectFull(id)
      set({ current, loading: false })
    } catch (e) {
      set({ error: e.message, loading: false, current: null })
    }
  },

  refreshCurrent: async () => {
    const { current } = get()
    if (current) await get().fetchCurrent(current.id)
  },

  createProject: async (name, color) => {
    const project = await api.projectCreate({ name, color })
    await get().fetchProjects()
    return project
  },

  updateProject: async (id, data) => {
    await api.projectUpdate(id, data)
    await get().fetchProjects()
    if (get().current?.id === id) await get().fetchCurrent(id)
  },

  deleteProject: async (id) => {
    await api.projectDelete(id)
    set((s) => ({ projects: s.projects.filter((p) => p.id !== id) }))
  },

  createSection: async (projectId, name) => {
    await api.sectionCreate(projectId, name)
    await get().refreshCurrent()
  },

  deleteSection: async (id) => {
    await api.sectionDelete(id)
    await get().refreshCurrent()
  },

  createTask: async (projectId, data) => {
    const task = await api.projectTaskCreate(projectId, data)
    await get().refreshCurrent()
    return task
  },

  updateTask: async (id, data) => {
    await api.projectTaskUpdate(id, data)
    await get().refreshCurrent()
  },

  deleteTask: async (id) => {
    await api.projectTaskDelete(id)
    await get().refreshCurrent()
  },

  addDependency: async (taskId, dependsOnId) => {
    await api.dependencyAdd(taskId, dependsOnId)
    await get().refreshCurrent()
  },

  removeDependency: async (taskId, dependsOnId) => {
    await api.dependencyRemove(taskId, dependsOnId)
    await get().refreshCurrent()
  },

  createStatusUpdate: async (projectId, status, body) => {
    await api.statusUpdateCreate(projectId, status, body)
    await get().refreshCurrent()
  },

  deleteStatusUpdate: async (id) => {
    await api.statusUpdateDelete(id)
    await get().refreshCurrent()
  },
}))
