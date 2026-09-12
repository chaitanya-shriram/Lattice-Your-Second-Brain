import { useEffect, useState } from 'react'
import { Users, Plus, Search, Mail, Building, Tag, X } from 'lucide-react'
import { api } from '../lib/api'
import { useAppStore } from '../stores/useAppStore'
import { cn } from '../lib/utils'

function ContactCard({ contact }) {
  const tags = contact.tags
    ? (typeof contact.tags === 'string' ? contact.tags.split(',').filter(Boolean) : contact.tags)
    : []

  return (
    <div className="bg-dark-surface border border-dark-border rounded-lg p-3 space-y-1.5 hover:border-lattice-700/40 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-medium text-dark-text">{contact.name}</p>
          {contact.role && (
            <p className="text-xs text-dark-subtle">{contact.role}</p>
          )}
        </div>
        <div className="shrink-0 w-8 h-8 rounded-full bg-lattice-700/30 flex items-center justify-center">
          <span className="text-xs font-bold text-lattice-300">
            {contact.name?.[0]?.toUpperCase() || '?'}
          </span>
        </div>
      </div>
      <div className="flex flex-wrap gap-2 text-[10px] text-dark-subtle">
        {contact.institution && (
          <span className="flex items-center gap-1">
            <Building size={9} />
            {contact.institution}
          </span>
        )}
        {contact.email && (
          <span className="flex items-center gap-1">
            <Mail size={9} />
            {contact.email}
          </span>
        )}
      </div>
      {contact.context && (
        <p className="text-xs text-dark-muted leading-relaxed">{contact.context}</p>
      )}
      {tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {tags.map((t) => (
            <span
              key={t}
              className="text-[10px] px-1.5 py-0.5 rounded bg-dark-card text-dark-subtle border border-dark-border/60"
            >
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}

function AddContactModal({ onClose, onSaved }) {
  const { addToast } = useAppStore()
  const [form, setForm] = useState({ name: '', role: '', institution: '', email: '', context: '', tags: '' })
  const [saving, setSaving] = useState(false)

  const save = async () => {
    if (!form.name.trim()) return
    setSaving(true)
    try {
      await api.crmUpsert({
        name: form.name.trim(),
        role: form.role || null,
        institution: form.institution || null,
        email: form.email || null,
        context: form.context || null,
        tags: form.tags ? form.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
      })
      addToast(`Contact saved: ${form.name}`, 'success')
      onSaved()
      onClose()
    } catch (e) {
      addToast(e.message, 'error')
    } finally {
      setSaving(false)
    }
  }

  const field = (key, placeholder, type = 'text') => (
    <div>
      <label className="text-[10px] text-dark-subtle uppercase tracking-wide">{key}</label>
      <input
        type={type}
        placeholder={placeholder}
        value={form[key]}
        onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
        className="w-full mt-0.5 bg-dark-card border border-dark-border rounded px-2 py-1.5 text-sm text-dark-text outline-none focus:border-lattice-600 transition-colors"
      />
    </div>
  )

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div className="bg-dark-surface border border-dark-border rounded-xl w-full max-w-sm p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-dark-text">Add / Update Contact</h2>
          <button onClick={onClose} className="text-dark-subtle hover:text-dark-text">
            <X size={16} />
          </button>
        </div>

        {field('name', 'Full name *')}
        {field('role', 'Role / Title')}
        {field('institution', 'University / Company')}
        {field('email', 'Email', 'email')}

        <div>
          <label className="text-[10px] text-dark-subtle uppercase tracking-wide">Context</label>
          <textarea
            placeholder="How you met, what to remember..."
            value={form.context}
            onChange={(e) => setForm((f) => ({ ...f, context: e.target.value }))}
            className="w-full mt-0.5 bg-dark-card border border-dark-border rounded px-2 py-1.5 text-sm text-dark-text outline-none focus:border-lattice-600 transition-colors resize-none min-h-[60px]"
          />
        </div>

        <div>
          <label className="text-[10px] text-dark-subtle uppercase tracking-wide">
            <Tag size={9} className="inline mr-1" />
            Tags (comma-separated)
          </label>
          <input
            placeholder="professor, quant, advisor"
            value={form.tags}
            onChange={(e) => setForm((f) => ({ ...f, tags: e.target.value }))}
            className="w-full mt-0.5 bg-dark-card border border-dark-border rounded px-2 py-1.5 text-sm text-dark-text outline-none focus:border-lattice-600 transition-colors"
          />
        </div>

        <div className="flex gap-2 pt-1">
          <button
            onClick={onClose}
            className="flex-1 py-1.5 rounded-md text-xs text-dark-subtle border border-dark-border hover:bg-dark-card transition-colors"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving || !form.name.trim()}
            className="flex-1 py-1.5 rounded-md text-xs font-medium bg-lattice-600 hover:bg-lattice-500 text-white disabled:opacity-40 transition-colors"
          >
            {saving ? 'Saving...' : 'Save Contact'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default function CRM() {
  const [contacts, setContacts] = useState([])
  const [search, setSearch] = useState('')
  const [showAdd, setShowAdd] = useState(false)
  const [loadError, setLoadError] = useState(null)

  const loadContacts = async (q = '') => {
    try {
      const data = await api.crmList(q)
      setContacts(data)
      setLoadError(null)
    } catch (e) {
      setLoadError(e.message)
    }
  }

  useEffect(() => {
    loadContacts()
  }, [])

  useEffect(() => {
    const t = setTimeout(() => loadContacts(search), 300)
    return () => clearTimeout(t)
  }, [search])

  return (
    <div className="p-4 space-y-4 max-w-2xl mx-auto">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Users size={18} className="text-lattice-400" />
          <h1 className="text-base font-semibold text-dark-text">People</h1>
          <span className="text-xs text-dark-subtle">({contacts.length})</span>
        </div>
        <button
          onClick={() => setShowAdd(true)}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium bg-lattice-600 hover:bg-lattice-500 text-white transition-colors"
        >
          <Plus size={12} />
          Add Contact
        </button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-dark-subtle" />
        <input
          type="text"
          placeholder="Search contacts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-8 pr-3 py-1.5 bg-dark-card border border-dark-border rounded-lg text-sm text-dark-text outline-none focus:border-lattice-600 transition-colors"
        />
      </div>

      {/* Grid */}
      {loadError ? (
        <div className="text-center py-12">
          <p className="text-sm text-red-400">Couldn't load contacts: {loadError}</p>
          <button onClick={() => loadContacts(search)} className="text-xs text-lattice-400 hover:text-lattice-300 mt-2">
            Retry
          </button>
        </div>
      ) : contacts.length === 0 ? (
        <div className="text-center py-12">
          <Users size={32} className="mx-auto text-dark-muted mb-2 opacity-30" />
          <p className="text-sm text-dark-subtle">No contacts yet.</p>
          <p className="text-xs text-dark-muted">Add people you meet — professors, researchers, peers.</p>
        </div>
      ) : (
        <div className="grid gap-2 sm:grid-cols-2">
          {contacts.map((c, i) => (
            <ContactCard key={c.id || i} contact={c} />
          ))}
        </div>
      )}

      {showAdd && (
        <AddContactModal onClose={() => setShowAdd(false)} onSaved={() => loadContacts(search)} />
      )}
    </div>
  )
}
