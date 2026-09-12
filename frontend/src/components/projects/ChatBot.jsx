import { useState, useRef, useEffect } from 'react'
import { Sparkles, X, Send } from 'lucide-react'
import { cn } from '../../lib/utils'
import { api } from '../../lib/api'
import { useProjectStore } from '../../stores/useProjectStore'
import { useTaskStore } from '../../stores/useTaskStore'
import { useAppStore } from '../../stores/useAppStore'

const GREETING = "Hi! Talk to me about anything — tasks, projects, deadlines, ideas, questions, reminders, or ask me what to focus on. I'll sort it into the right dashboard."

export default function ChatBot() {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState([{ role: 'user', content: GREETING }])
  const [input, setInput] = useState('')
  const [thinking, setThinking] = useState(false)
  const bottomRef = useRef(null)
  const started = useRef(false)
  const { fetchProjects, fetchHome, refreshCurrent, fetchMyTasks } = useProjectStore()
  const { fetch: fetchTasks, fetchStats: fetchTaskStats } = useTaskStore()
  const { addToast } = useAppStore()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, thinking])

  const send = async (history) => {
    setThinking(true)
    try {
      const res = await api.projectChat(history)
      setMessages((m) => [...m, { role: 'assistant', content: res.reply }])
      fetchProjects()
      fetchHome()
      fetchMyTasks()
      refreshCurrent()
      fetchTasks({ status: 'pending' })
      fetchTaskStats()
    } catch (e) {
      addToast(e.message, 'error')
      setMessages((m) => [...m, { role: 'assistant', content: `Error: ${e.message}` }])
    }
    setThinking(false)
  }

  useEffect(() => {
    if (open && !started.current) {
      started.current = true
      send(messages)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open])

  const submit = (e) => {
    e.preventDefault()
    if (!input.trim() || thinking) return
    const next = [...messages, { role: 'user', content: input.trim() }]
    setMessages(next)
    setInput('')
    send(next)
  }

  const visible = messages.filter((m, i) => !(i === 0 && m.role === 'user' && m.content === GREETING))

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-5 right-5 z-50 w-11 h-11 rounded-full bg-lattice-600 hover:bg-lattice-500 text-white flex items-center justify-center shadow-lg transition-colors"
      >
        {open ? <X size={18} /> : <Sparkles size={18} />}
      </button>

      {open && (
        <div className="fixed bottom-20 right-5 z-50 w-[380px] h-[520px] max-w-[calc(100vw-40px)] bg-dark-surface border border-dark-border rounded-xl shadow-2xl flex flex-col overflow-hidden">
          <div className="h-10 flex items-center px-3 border-b border-dark-border/60 shrink-0">
            <Sparkles size={13} className="text-lattice-400 mr-1.5" />
            <span className="text-xs font-semibold text-dark-text">Assistant</span>
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
            {visible.map((m, i) => (
              <div key={i} className={cn('flex', m.role === 'user' ? 'justify-end' : 'justify-start')}>
                <div className={cn(
                  'max-w-[85%] rounded-lg px-2.5 py-1.5 text-sm whitespace-pre-wrap',
                  m.role === 'user'
                    ? 'bg-gradient-to-br from-lattice-600 to-lattice-700 text-white'
                    : 'bg-dark-card border border-dark-border/60 text-dark-text'
                )}>
                  {m.content}
                </div>
              </div>
            ))}
            {thinking && (
              <div className="flex justify-start">
                <div className="bg-dark-card border border-dark-border/60 rounded-lg px-2.5 py-1.5 text-xs text-dark-subtle animate-pulse-slow">
                  thinking…
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={submit} className="flex items-center gap-1.5 p-2 border-t border-dark-border/60 shrink-0">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type an update or ask a question…"
              className="input-base flex-1"
              disabled={thinking}
            />
            <button type="submit" disabled={!input.trim() || thinking} className="btn-primary px-2.5">
              <Send size={14} />
            </button>
          </form>
        </div>
      )}
    </>
  )
}
