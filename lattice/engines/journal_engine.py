"""
Journal Engine: conversational daily journal with LLM reflection prompts.
Entries are stored in vault/01-daily/{date}.md and a Journal table (via BrainDump.source='journal').
"""
import uuid
from pathlib import Path
from datetime import datetime, date

from config.settings import get_settings
from storage.database import get_db
from storage.models import BrainDump
from llm.router import get_llm
from engines.vault_writer import get_vault_writer
from utils.logger import get_logger

log = get_logger("engines.journal_engine")

JOURNAL_REFLECTION_SYSTEM = """You are a thoughtful journaling companion for a graduate student
who uses a second brain system. Your role is to ask one deep, specific follow-up question
that helps them reflect on what they wrote. Be concise (1-2 sentences).
Do not give advice or summaries — only ask a question that deepens reflection."""

JOURNAL_SUMMARY_SYSTEM = """You are summarizing a journal entry for a second brain system.
Extract key themes, emotions, decisions made, and any action items mentioned.
Return plain text, 3-5 bullet points maximum."""


class JournalEngine:
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm()
        self.vault = get_vault_writer()

    async def add_entry(self, text: str, prompt_reflection: bool = True) -> dict:
        """Add a journal entry to today's daily note and get reflection prompt."""
        today = date.today()
        now = datetime.utcnow().isoformat()

        # Ensure daily note exists
        daily_path = self.vault.write_daily_note(today)

        # Append entry to daily note
        entry_md = f"\n\n### Journal Entry — {datetime.now().strftime('%H:%M')}\n{text}\n"
        daily_full = self.settings.vault_path / daily_path
        with open(str(daily_full), "a", encoding="utf-8") as f:
            f.write(entry_md)

        # Get reflection prompt from LLM
        reflection = ""
        if prompt_reflection:
            try:
                reflection = await self.llm.complete(
                    f"Journal entry:\n{text}",
                    system=JOURNAL_REFLECTION_SYSTEM,
                )
            except Exception as e:
                log.warning(f"Reflection prompt failed: {e}")
                reflection = "What surprised you most about today?"

        # Store in SQLite as BrainDump with source='journal'
        with get_db() as db:
            dump = BrainDump(
                id=str(uuid.uuid4()),
                raw_text=text,
                source="journal",
                items_extracted=0,
                created_at=now,
            )
            db.add(dump)

        log.info(f"Journal entry added to {daily_path}")
        return {
            "daily_note": daily_path,
            "entry_length": len(text),
            "reflection_prompt": reflection,
            "timestamp": now,
        }

    async def get_today_summary(self) -> dict:
        """Summarize today's journal entries."""
        today = date.today()
        daily_path = self.settings.vault_path / f"01-daily/{today.isoformat()}.md"

        if not daily_path.exists():
            return {"summary": "No journal entries today.", "date": today.isoformat()}

        content = daily_path.read_text(encoding="utf-8")
        try:
            summary = await self.llm.complete(
                f"Today's notes:\n{content[:3000]}",
                system=JOURNAL_SUMMARY_SYSTEM,
            )
        except Exception as e:
            summary = f"Error generating summary: {e}"

        return {
            "date": today.isoformat(),
            "summary": summary,
            "note_path": str(daily_path),
        }

    def get_entries(self, limit: int = 10) -> list[dict]:
        """Return recent journal entries."""
        with get_db() as db:
            entries = (
                db.query(BrainDump)
                .filter(BrainDump.source == "journal")
                .order_by(BrainDump.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": e.id,
                    "preview": e.raw_text[:100] + "..." if len(e.raw_text) > 100 else e.raw_text,
                    "created_at": e.created_at,
                }
                for e in entries
            ]


_engine: JournalEngine | None = None


def get_journal_engine() -> JournalEngine:
    global _engine
    if _engine is None:
        _engine = JournalEngine()
    return _engine
