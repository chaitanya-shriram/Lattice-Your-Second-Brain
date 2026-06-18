from pathlib import Path
from datetime import datetime
from typing import Any
import json

from config.settings import get_settings
from utils.markdown_utils import build_frontmatter, parse_frontmatter
from utils.logger import get_logger

log = get_logger("engines.vault_writer")


class VaultWriter:
    def __init__(self):
        self.settings = get_settings()
        self.vault = self.settings.vault_path

    def _write(self, rel_path: str, content: str) -> Path:
        full = self.vault / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content, encoding="utf-8")
        log.debug(f"Wrote: {rel_path}")
        return full

    def _read(self, rel_path: str) -> str | None:
        full = self.vault / rel_path
        if full.exists():
            return full.read_text(encoding="utf-8")
        return None

    # ── Tasks ─────────────────────────────────────────────────────────

    def write_task_note(self, task: dict) -> str:
        """Write/update task note in 02-tasks/{bucket}/."""
        bucket = task.get("bucket", "daily")
        title_slug = self._slugify(task["title"])
        rel = f"02-tasks/{bucket}/{title_slug}.md"

        meta = {
            "type": "task",
            "id": task["id"],
            "title": task["title"],
            "bucket": bucket,
            "priority": task.get("priority", "medium"),
            "status": task.get("status", "inbox"),
            "topic": task.get("topic"),
            "domain": task.get("domain", "academic"),
            "deadline": task.get("deadline"),
            "source": task.get("source", "desktop"),
            "tags": task.get("tags", []),
            "created_at": task.get("created_at", datetime.utcnow().date().isoformat()),
        }

        body = f"# {task['title']}\n\n"
        if task.get("description"):
            body += f"{task['description']}\n\n"
        body += "## Notes\n\n"

        self._write(rel, build_frontmatter(meta) + body)
        return rel

    # ── Questions ─────────────────────────────────────────────────────

    def append_question(self, question: dict) -> str:
        """Append question to 03-questions/{topic}.md."""
        topic = question.get("topic", "general").replace("/", "-").replace(" ", "-")
        rel = f"03-questions/{topic}.md"

        existing = self._read(rel) or f"---\ntype: questions\ntopic: {topic}\n---\n\n# Questions — {topic.title()}\n\n"

        entry = f"\n## Q: {question['text']}\n\n"
        entry += f"> [!question]\n"
        entry += f"> added: {datetime.utcnow().date().isoformat()}\n"
        if question.get("source"):
            entry += f"> source: {question['source']}\n"
        entry += f"> status: unsolved\n\n"
        entry += "**My current understanding:**\n\n\n"

        content = existing.rstrip() + "\n" + entry
        self._write(rel, content)
        return rel

    # ── Ideas ──────────────────────────────────────────────────────────

    def append_idea(self, idea: dict) -> str:
        """Append idea to 04-ideas/{topic}.md."""
        topic = idea.get("topic", "general").replace("/", "-").replace(" ", "-")
        rel = f"04-ideas/{topic}.md"

        existing = self._read(rel) or f"---\ntype: ideas\ntopic: {topic}\n---\n\n# Ideas — {topic.title()}\n\n"

        entry = f"\n### {datetime.utcnow().date().isoformat()}\n{idea['text']}\n"
        content = existing.rstrip() + "\n" + entry
        self._write(rel, content)
        return rel

    # ── Fleeting ───────────────────────────────────────────────────────

    def append_fleeting(self, item: dict) -> str:
        today = datetime.utcnow().date().isoformat()
        rel = f"10-fleeting/{today}.md"

        existing = self._read(rel) or f"---\ntype: fleeting\ndate: {today}\n---\n\n# Fleeting — {today}\n\n"
        entry = f"- {item['text']}\n"
        content = existing.rstrip() + "\n" + entry
        self._write(rel, content)
        return rel

    # ── References / Reading list ──────────────────────────────────────

    def append_reading_list(self, ref: dict) -> str:
        rel = "09-bibliography/reading-list.md"
        existing = self._read(rel) or "---\ntype: reading-list\n---\n\n# Reading List\n\n"
        action = ref.get("action", "read")
        author = f" — {ref['author']}" if ref.get("author") else ""
        entry = f"- [ ] [{ref['title']}]{author} `{ref.get('type','other')}` `{action}`\n"
        content = existing.rstrip() + "\n" + entry
        self._write(rel, content)
        return rel

    # ── Wiki pages ─────────────────────────────────────────────────────

    def write_wiki_page(self, page: dict) -> str:
        """Write a compiled wiki page to 00-wiki/{folder}/{filename}.md."""
        folder = page.get("folder", "general")
        filename = page.get("filename", self._slugify(page.get("title", "untitled")))
        rel = f"00-wiki/{folder}/{filename}.md"

        meta = {
            "type": "wiki-page",
            "concept": page.get("title", filename),
            "folder": folder,
            "domain": page.get("domain", "academic"),
            "related_concepts": page.get("related_concepts", []),
            "confidence": page.get("confidence", "medium"),
            "has_contradictions": False,
            "version": 1,
            "compiled_at": datetime.utcnow().isoformat(),
        }

        existing = self._read(rel)
        if existing:
            existing_meta, _ = parse_frontmatter(existing)
            meta["version"] = existing_meta.get("version", 1) + 1

        content = build_frontmatter(meta) + page.get("content", f"# {page.get('title', filename)}\n\n")
        self._write(rel, content)
        return rel

    def update_wiki_page(self, path: str, additions: str, contradictions: list[str] | None = None) -> str:
        """Append additions to existing wiki page."""
        rel = path.replace("\\", "/")
        existing = self._read(rel)
        if not existing:
            log.warning(f"Wiki page not found for update: {rel}")
            return rel

        meta, body = parse_frontmatter(existing)
        meta["version"] = meta.get("version", 1) + 1
        if contradictions:
            meta["has_contradictions"] = True

        new_body = body.rstrip() + "\n\n" + additions.strip() + "\n"
        if contradictions:
            new_body += "\n\n> [!warning] Potential contradictions\n"
            for c in contradictions:
                new_body += f"> - {c}\n"

        self._write(rel, build_frontmatter(meta) + new_body)
        return rel

    # ── Daily note ─────────────────────────────────────────────────────

    def write_daily_note(self, date: str | None = None) -> str:
        date = date or datetime.utcnow().date().isoformat()
        rel = f"01-daily/{date}.md"
        if self._read(rel):
            return rel  # already exists

        meta = {
            "type": "daily",
            "date": date,
            "mood": None,
            "energy": None,
            "focus_time_hours": 0,
            "tasks_planned": 0,
            "tasks_completed": 0,
        }
        body = f"# Daily Note — {date}\n\n## Today's Focus\n\n\n## Notes\n\n\n## End of Day\n\n"
        self._write(rel, build_frontmatter(meta) + body)
        return rel

    # ── Book / Paper notes ─────────────────────────────────────────────

    def write_book_note(self, metadata: dict, folder: str) -> str:
        title = metadata.get("title", "Unknown")
        filename = metadata.get("canonical_filename", self._slugify(title))
        rel = f"{folder}/{filename}.md"

        meta = {
            "type": "book",
            "title": title,
            "author": metadata.get("authors", []),
            "year": metadata.get("year"),
            "publisher": metadata.get("publisher"),
            "edition": metadata.get("edition"),
            "topics": metadata.get("primary_topics", []),
            "status": "unread",
            "progress": 0.0,
            "source_file": metadata.get("canonical_filename", ""),
            "added": datetime.utcnow().date().isoformat(),
            "lattice_id": f"book_{self._slugify(title)[:30]}",
        }

        body = f"# {title}\n\n"
        if metadata.get("brief_description"):
            body += f"{metadata['brief_description']}\n\n"
        body += "## Summary\n\n\n## Key Concepts\n\n\n## Notes\n\n\n## Quotes\n\n"

        self._write(rel, build_frontmatter(meta) + body)
        return rel

    def write_paper_note(self, metadata: dict, folder: str) -> str:
        title = metadata.get("title", "Unknown")
        filename = metadata.get("canonical_filename", self._slugify(title))
        rel = f"{folder}/{filename}.md"

        meta = {
            "type": "paper",
            "title": title,
            "author": metadata.get("authors", []),
            "year": metadata.get("year"),
            "topics": metadata.get("primary_topics", []),
            "status": "unread",
            "source_file": metadata.get("canonical_filename", ""),
            "added": datetime.utcnow().date().isoformat(),
            "lattice_id": f"paper_{self._slugify(title)[:30]}",
        }

        body = f"# {title}\n\n"
        if metadata.get("brief_description"):
            body += f"{metadata['brief_description']}\n\n"
        body += "## Abstract / Summary\n\n\n## Key Contributions\n\n\n## Notes\n\n\n## Quotes\n\n"

        self._write(rel, build_frontmatter(meta) + body)
        return rel

    # ── Bibliography ───────────────────────────────────────────────────

    def append_bibliography(self, metadata: dict, note_path: str) -> str:
        rel = "09-bibliography/bibliography.md"
        existing = self._read(rel) or "---\ntype: bibliography\n---\n\n# Bibliography\n\n## Books\n\n## Papers\n\n"

        doc_type = metadata.get("document_type", "unknown")
        authors = ", ".join(metadata.get("authors", []))
        year = metadata.get("year", "")
        title = metadata.get("title", "Unknown")
        filename = metadata.get("canonical_filename", "")
        note_link = f"[[{Path(note_path).stem}]]" if note_path else ""

        entry = f"\n### {filename}\n"
        entry += f"**{title}**\n"
        entry += f"{authors} ({year}).\n"
        if metadata.get("publisher"):
            entry += f"{metadata['publisher']}.\n"
        topics = " ".join(f"#{t}" for t in metadata.get("primary_topics", []))
        entry += f"Topics: {topics}\n"
        entry += f"Status: unread | {note_link}\n"

        section = "## Books" if "book" in doc_type else "## Papers"
        content = existing.replace(section, section + entry)
        self._write(rel, content)
        return rel

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _slugify(text: str) -> str:
        import re
        text = text.lower().strip()
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text)
        return re.sub(r'-+', '-', text).strip('-')[:60]


_writer: VaultWriter | None = None


def get_vault_writer() -> VaultWriter:
    global _writer
    if _writer is None:
        _writer = VaultWriter()
    return _writer
