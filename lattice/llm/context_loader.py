"""
Session Context Loader: builds the system prompt context injected into every LLM call.
Loads lattice-context.md + memory.md + agent config + today's tasks.
"""
from pathlib import Path
from datetime import datetime

from config.settings import get_settings
from utils.logger import get_logger

log = get_logger("llm.context_loader")

_MAX_MEMORY_LINES = 50
_MAX_TASKS = 10


class ContextLoader:
    def __init__(self):
        self.settings = get_settings()

    def load(self) -> str:
        """Build full session context string for LLM system prompt injection."""
        parts = []

        # [1] Lattice identity
        lattice_ctx = self._load_lattice_context()
        if lattice_ctx:
            parts.append(lattice_ctx)

        # [2] Recent memory
        memory = self._load_memory()
        if memory:
            parts.append(memory)

        # [3] Today's tasks
        tasks_ctx = self._load_today_tasks()
        if tasks_ctx:
            parts.append(tasks_ctx)

        # [4] Current date/time
        now = datetime.now().strftime("%A, %B %d %Y %H:%M")
        parts.append(f"## Current Time\n{now}")

        return "\n\n".join(parts)

    def _load_lattice_context(self) -> str:
        """Load _context/lattice-context.md."""
        path = self.settings.context_path / "lattice-context.md"
        if path.exists():
            content = path.read_text(encoding="utf-8")
            return f"## Lattice Context\n{content[:2000]}"

        # Auto-generate if missing
        self._generate_lattice_context()
        return ""

    def _generate_lattice_context(self):
        """Write a default lattice-context.md."""
        context_path = self.settings.context_path
        context_path.mkdir(parents=True, exist_ok=True)
        path = context_path / "lattice-context.md"

        content = """# Lattice — Your Second Brain

## Identity
Lattice is a local-only AI knowledge operating system. It helps capture, process, connect, and review information.

## Domains
- Academic: mathematics, probability, information theory, machine learning, CS
- Finance: quantitative finance, derivatives, trading
- Projects: ongoing work and assignments

## Operating Principles
- All data stays local (no cloud, no external APIs in production)
- Karpathy compilation: raw sources → structured wiki pages
- Graph-enhanced RAG: wiki search + concept edge expansion
- Task management: inbox → daily → weekly → long-term → someday buckets

## Vault Structure
- 00-wiki/: compiled knowledge pages
- 01-daily/: daily notes and reviews
- 02-tasks/: task notes
- 05-books/, 06-papers/: ingested files
- _context/: this file + memory log
- _skills/: reusable skill definitions
"""
        path.write_text(content, encoding="utf-8")
        log.info("Generated default lattice-context.md")

    def _load_memory(self) -> str:
        """Load last N lines from _context/memory.md."""
        path = self.settings.context_path / "memory.md"
        if not path.exists():
            return ""
        lines = path.read_text(encoding="utf-8").splitlines()
        recent = lines[-_MAX_MEMORY_LINES:]
        return "## Recent Memory\n" + "\n".join(recent)

    def _load_today_tasks(self) -> str:
        """Load pending daily tasks from SQLite."""
        try:
            from storage.database import get_db
            from storage.models import Task
            from datetime import date

            today = date.today().isoformat()
            with get_db() as db:
                tasks = (
                    db.query(Task)
                    .filter(Task.bucket == "daily", Task.status != "done")
                    .limit(_MAX_TASKS)
                    .all()
                )
                task_lines = [f"- [{t.priority}] {t.title}" for t in tasks]

            if task_lines:
                return "## Today's Tasks\n" + "\n".join(task_lines)
        except Exception as e:
            log.warning(f"Could not load tasks: {e}")
        return ""


_loader: ContextLoader | None = None


def get_context_loader() -> ContextLoader:
    global _loader
    if _loader is None:
        _loader = ContextLoader()
    return _loader


def build_session_context() -> str:
    """Convenience function: build full session context string."""
    return get_context_loader().load()
