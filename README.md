# Lattice — Your Second Brain

> A local-first AI knowledge OS. Runs entirely on your machine. No cloud, no subscriptions, no data leaving your device.

Built for students and researchers who want a personal knowledge base that thinks with them.

---

## Features

| Feature | What it does |
|---|---|
| **Brain Dump** | Paste anything (notes, ideas, tasks, questions). LLM parses and routes it automatically. |
| **Ask** | Query your vault with natural language. Graph-expanded RAG with cited sources. |
| **Wiki** | Upload PDFs/docs → LLM compiles wiki pages with cross-links and `[[concept]]` citations. |
| **Tasks** | Extracted from brain dumps. Daily/weekly/long-term/someday buckets with priority. |
| **Projects** | Asana-style project manager: sections, kanban, milestones, dependencies, status updates, chat control-center. |
| **Intent Planning** | Say "I'm going to build X" in a Brain Dump — a scheduled job drafts a plan with Ollama and turns it into a Project + vault note automatically. |
| **Graph** | D3 force-directed concept map showing relationships between wiki pages. |
| **Journal** | Daily entries with optional AI reflection. |
| **People (CRM)** | Lightweight contact notes for researchers, professors, collaborators. |
| **Daily Review** | Auto-generated at a set time: what you did, what slipped, tomorrow's priorities. |
| **Vault Health** | Finds broken links, orphaned notes, contradictions, knowledge gaps. |
| **Git auto-commit** | Vault changes committed every hour, full history preserved. |

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, SQLAlchemy, SQLite |
| LLM | Ollama (`qwen2.5:14b`) |
| Embeddings | `nomic-embed-text` via Ollama |
| Frontend | React 18, Vite, TailwindCSS, Zustand, D3.js |
| Scheduler | APScheduler |
| File watching | watchdog |

Everything runs locally. Zero external API calls in production.

---

## Requirements

- Python 3.11+
- [Ollama](https://ollama.ai) running locally
- Node.js 18+ (only needed to build the frontend)

Pull the models:

```bash
ollama pull qwen2.5:14b
ollama pull nomic-embed-text
```

---

## Setup

```bash
# 1. Clone
git clone https://github.com/chaitanya-shriram/lattice.git
cd lattice

# 2. Python dependencies
cd lattice
pip install -r requirements.txt

# 3. Configure paths
cp .env.example .env
# Edit .env — set VAULT_PATH, VAULT_FILES_PATH, INCOMING_PATH, DB_PATH, LOGS_PATH

# 4. Build frontend (one-time)
cd ../frontend
npm install
npm run build

# 5. Start
cd ../lattice
python main.py
```

Open `http://localhost:8080` in your browser.

On Windows, double-click `start_lattice.bat` instead of steps 5.

---

## First Run

After `python main.py` and browser opens at `http://localhost:8080`:

1. Go to **Settings** — verify Ollama shows "connected"
2. Edit `vault/_context/lattice-context.md` — add your name, domains, active projects (this file is injected into every LLM prompt)
3. Drop a file or type something in Brain Dump to ingest first content

---

## Usage Guide

### Brain Dump

Type anything — tasks, ideas, questions, links, random thoughts. Press **Ctrl+Enter** or click **Process**.

LLM parses and routes automatically:
- Tasks → Tasks page (assigned to a bucket: daily/weekly/long-term/someday)
- Questions → logged as open questions in vault
- Ideas → stored in vault as idea notes

No structure needed. Write like you think.

### Ask

Type a natural language question. Lattice runs graph-expanded RAG:

1. Embeds query → semantic search over wiki pages
2. Expands results via concept graph (pulls in linked pages)
3. LLM synthesizes answer, cites sources as `[[page-name]]`

Answer quality depends on how much is in your vault. Ingest more files = better answers.

### Wiki

Auto-compiled from ingested files. Never write wiki pages manually.

**How to populate:**
1. Drop PDF/EPUB/DOCX/TXT into `incoming/` folder — or use the **Drop Files** zone on Dashboard
2. Lattice detects file, extracts text + metadata
3. LLM compiles structured wiki pages into `vault/00-wiki/`
4. Pages cross-link with `[[concept]]` notation
5. Appears in Wiki tab with full-text search

### Tasks

Four buckets:
| Bucket | Meaning |
|---|---|
| **Daily** | Do today |
| **Weekly** | Do this week |
| **Long-term** | Ongoing projects |
| **Someday** | Backlog / maybe |

Populated from Brain Dumps automatically. Priority levels: `urgent` / `high` / `normal` / `low`. Click to complete, drag to reprioritize.

### Projects

Asana-style multi-project manager, separate from the brain-dump Tasks buckets above — for planned work with structure (sections, milestones, dependencies) rather than quick-capture.

- **Home** — kanban with one column per project (progress bar, latest status, pending tasks) or a flat list of all pending tasks
- **Per-project** — List (grouped by section), Kanban (drag-free — move tasks via the task panel's section dropdown), and Status (update log: on track / at risk / off track / complete)
- **Task detail panel** — due date, priority, effort, tags, milestone flag, notes, dependencies ("blocked by"), subtasks
- **Personal** — built-in inbox project for standalone tasks, cannot be deleted
- **Chat control-center** — floating ✦ button, walks pending work, creates/edits projects and tasks via conversation, routed through Lattice's own LLM router (`llm/router.py`). Deletions only apply when the item's exact name appears in your own message (project deletion additionally requires the word "project"), so a confused model can't nuke the wrong thing.

### Intent Planning

Brain Dump detects stated commitments — not one-off tasks, but things like "I'm going to build a trading bot" — and queues them as pending intents. Every `INTENT_PLANNING_INTERVAL_MINUTES` (default 30), a scheduled job sweeps pending intents and, for each: asks Ollama to draft a plan (description, phases, 5-15 concrete tasks), creates a matching Project with sections/tasks, and writes a plan note to `vault/08-projects/`. Auto-planned items show up on the Dashboard under "Auto-planned," linking straight to the generated Project. Trigger it manually with `POST /api/intents/run-now` instead of waiting for the schedule.

### Graph

D3 force-directed concept map. Nodes = wiki pages. Edges = `[[concept]]` links between pages.

- Click node → opens wiki page
- Zoom and pan to explore clusters
- Tightly connected clusters = dense knowledge areas
- Isolated nodes = orphaned notes (Vault Health will flag these)

### Journal

Daily entries stored in `vault/01-daily/YYYY-MM-DD.md`. Write manually or click **AI Reflect** to generate a reflection from today's Brain Dumps and completed tasks.

### People (CRM)

Lightweight contact notes for researchers, professors, collaborators. Each person gets a markdown file in `vault/07-people/`. Fields: name, role, relationship, tags, notes. No sync to any external service.

### Daily Review

Auto-generated at `DAILY_REVIEW_TIME` (default `21:00`). Contains:
- Tasks completed today
- Tasks that slipped (pending + overdue)
- Suggested priorities for tomorrow

Also available on-demand from Dashboard. Stored in vault as a daily note.

### Vault Health

Runs at `NIGHTLY_MAINTENANCE_TIME` (default `23:00`). Scans for:
- **Broken links** — `[[references]]` pointing to non-existent pages
- **Orphaned notes** — pages with no inbound or outbound links
- **Knowledge gaps** — topics referenced but never compiled
- **Contradictions** — LLM flags conflicting statements across pages

View reports in the Vault Health section. Fix broken links by creating the missing pages or correcting the reference.

### Files

Upload via Dashboard drop zone or directly into `incoming/`. Supported: PDF, EPUB, DOCX, TXT, MD.

Pipeline:
1. File saved to `vault-files/`
2. Watcher detects `incoming/` drop
3. Metadata extracted (title, author, type)
4. Wiki pages compiled from content
5. Original moved to `vault/00-raw/processed/`

Track ingestion status on the Files page.

---

## Configuration

All settings live in `lattice/.env`. Copy from `lattice/.env.example` to get started.

### Required paths

```env
VAULT_PATH=/path/to/your/vault          # where markdown files live
VAULT_FILES_PATH=/path/to/vault-files   # raw uploaded files
INCOMING_PATH=/path/to/incoming         # drop files here to auto-ingest
DB_PATH=/path/to/lattice/data/lattice.db
LOGS_PATH=/path/to/logs
```

### LLM settings

```env
LLM_BACKEND=ollama                      # or "claude" for Anthropic (dev/testing)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_PRIMARY_MODEL=qwen2.5:14b        # change to any model you have pulled
OLLAMA_EMBED_MODEL=nomic-embed-text
ANTHROPIC_API_KEY=                      # only needed if LLM_BACKEND=claude
```

### Scheduling

```env
WORK_START=09:00                        # check-in window start
WORK_END=22:00                          # check-in window end
CHECKIN_INTERVAL_MINUTES=120            # how often to nudge for brain dumps
DAILY_REVIEW_TIME=21:00                 # when to generate daily review (24h)
NIGHTLY_MAINTENANCE_TIME=23:00          # vault cleanup time
```

### Server

```env
API_HOST=0.0.0.0    # 0.0.0.0 = LAN accessible (phone on same WiFi)
API_PORT=8080
DEBUG=true
```

### Feature flags

```env
GIT_VERSIONING_ENABLED=true    # hourly auto-commit of vault changes
WIKI_COMPILATION_ENABLED=true  # auto-compile wiki pages from ingested files
SELF_IMPROVE_ENABLED=true      # nightly vault health check (broken links, orphans, gaps)
```

---

## Vault structure

Lattice manages a vault folder you point it to:

```
vault/
  00-raw/          # incoming files before processing
    processed/     # moved here after ingestion
  00-wiki/         # compiled wiki pages (auto-generated by LLM)
    topic/         # grouped by domain
  01-daily/        # daily notes (YYYY-MM-DD.md)
  02-tasks/        # task notes (daily/, weekly/, long-term/, someday/)
  05-books/        # ingested books
  06-papers/       # ingested papers
  07-people/       # CRM contact notes
  08-projects/     # project docs
  _context/        # lattice-context.md + memory.md (LLM system prompt context)
  _skills/         # reusable skill definitions (Markdown prompts)
```

Drop any PDF, markdown, or text file into `incoming/`. Lattice picks it up, extracts metadata, compiles wiki pages, and moves it to the right vault folder.

---

## API

FastAPI with auto-generated docs at `http://localhost:8080/docs`.

```
POST /api/dump/               brain dump (text → parsed tasks/questions/ideas)
POST /api/graph/query         RAG query (natural language → cited answer)
GET  /api/tasks/              list tasks
PATCH /api/tasks/{id}         update task (complete, reprioritize, etc.)
GET  /api/wiki/               list wiki pages
GET  /api/wiki/{page}         get wiki page content
GET  /api/graph/              graph data for D3 visualization
POST /api/files/upload        upload a file for ingestion
POST /api/journal/            add journal entry
GET  /api/journal/            list journal entries
GET  /api/vault-health/reports  vault health reports
GET  /api/health/             system health check
GET  /api/projects/           list projects
GET  /api/projects/home       home board (per-project progress, latest status)
GET  /api/projects/my-tasks   all pending tasks across projects
POST /api/projects/           create project
GET  /api/projects/{id}/full  project with sections, tasks, dependencies, updates
POST /api/projects/{id}/tasks create task in project
PATCH /api/projects/tasks/{id} update task (complete, reprioritize, move, etc.)
POST /api/projects/chat       chat control-center (Ollama-backed)
GET  /api/intents/            list detected intents + their planning status
POST /api/intents/run-now     trigger the intent-planning sweep immediately
POST /api/daily-review/generate  generate today's review on demand (same engine as the 21:00 job)
```

---

## Customizing

### Change the LLM model

Edit `OLLAMA_PRIMARY_MODEL` in `.env`. Any model you have pulled in Ollama works:

```env
OLLAMA_PRIMARY_MODEL=llama3.2:latest
```

### Add a skill

Skills are Markdown files in `vault/_skills/`. Each one is a named prompt template the LLM can invoke. Example `vault/_skills/summarize.md`:

```markdown
---
name: summarize
description: Summarize a text into bullet points
---

Summarize the following in 5 bullet points. Be concise and precise:

{{input}}
```

### Customize LLM prompts

All LLM prompt templates are in `lattice/config/prompts.py`. Edit them directly — no restart needed for most changes (prompts are loaded per-request).

### Add identity context

Edit `vault/_context/lattice-context.md`. This file is injected into every LLM system prompt, so Lattice knows about your domains, projects, and goals.

---

## Running tests

```bash
cd lattice
python -m pytest tests/ -v
```

61 tests. All pass without Ollama running (LLM calls are mocked in tests).

---

## Windows autostart

Import `lattice_autostart.xml` into Task Scheduler to start Lattice on login:

```powershell
schtasks /create /xml lattice_autostart.xml /tn "Lattice"
```

Or run manually:

```powershell
.\start_lattice.ps1
```

---

## Project layout

```
lattice/           ← root
  lattice/         ← Python backend
    api/           # FastAPI route handlers
    config/        # settings.py, prompts.py
    engines/       # brain_dump, rag, graph, wiki, scheduler, intent_planner, crm, journal...
    llm/           # Ollama router, embeddings, context loader
    storage/       # SQLAlchemy models, database init
    tests/         # 69 tests
    main.py        # FastAPI app entry point
    requirements.txt
    .env           # your local config (gitignored)
    .env.example   # template
  frontend/        ← React UI
    src/
      pages/       # Dashboard, Ask, Tasks, Projects, ProjectDetail, Wiki, Graph, Journal, CRM, Settings, Files
      components/  # Sidebar, StatusBar, Toast, Card, projects/ (kanban, list, status, chat)
      stores/      # Zustand state (tasks, projects, app)
      lib/         # api.js (fetch wrappers), utils.js
    index.html
    tailwind.config.js
    vite.config.js
  vault/           ← your knowledge (gitignored by default)
  vault-files/     ← raw uploaded files (gitignored)
  incoming/        ← drop zone for auto-ingestion (gitignored)
  logs/            ← lattice.log, llm.log (gitignored)
  start_lattice.bat
  start_lattice.ps1
  lattice_autostart.xml
```

---

## License

MIT
