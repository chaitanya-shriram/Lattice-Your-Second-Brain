"""
Daily review generator: LLM synthesizes today's activity into a structured review.
Writes into vault/01-daily/{date}.md. Called by scheduler at DAILY_REVIEW_TIME.
"""
from datetime import datetime, date
from pathlib import Path

from config.settings import get_settings
from config.prompts import DAILY_REVIEW_SYSTEM, DAILY_REVIEW_USER
from storage.database import get_db
from storage.models import Task, BrainDump, WikiPage
from llm.router import get_llm
from engines.vault_writer import get_vault_writer
from utils.logger import get_logger

log = get_logger("engines.daily_review")


class DailyReviewEngine:
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm()
        self.vault = get_vault_writer()

    async def generate(self, review_date: date = None) -> dict:
        """Generate daily review note for given date (default: today)."""
        if review_date is None:
            review_date = date.today()

        date_str = review_date.isoformat()
        log.info(f"Generating daily review for {date_str}")

        # Ensure note exists
        daily_path = self.vault.write_daily_note(review_date)

        # Gather today's activity
        activity = self._gather_activity(date_str)

        # Build context
        context = self._build_context(activity, date_str)

        # LLM synthesis
        try:
            prompt = DAILY_REVIEW_USER.format(
                date=date_str,
                context=context,
            )
            review_text = await self.llm.complete(prompt, system=DAILY_REVIEW_SYSTEM)
        except Exception as e:
            log.error(f"Daily review LLM call failed: {e}")
            review_text = self._fallback_review(activity, date_str)

        # Write review into daily note
        full_path = self.settings.vault_path / daily_path
        timestamp = datetime.now().strftime("%H:%M")
        review_section = f"\n\n---\n\n## Daily Review — {timestamp}\n\n{review_text}\n"

        with open(str(full_path), "a", encoding="utf-8") as f:
            f.write(review_section)

        log.info(f"Daily review written to {daily_path}")
        return {
            "date": date_str,
            "daily_note": daily_path,
            "tasks_completed": activity["tasks_completed"],
            "brain_dumps": activity["brain_dumps"],
            "wiki_pages_compiled": activity["wiki_pages_new"],
            "review_length": len(review_text),
        }

    def _gather_activity(self, date_str: str) -> dict:
        """Pull today's data from SQLite."""
        with get_db() as db:
            # Completed tasks
            tasks_done = db.query(Task).filter(
                Task.status == "done",
                Task.completed_at.like(f"{date_str}%"),
            ).all()
            tasks_done_data = [{"title": t.title, "priority": t.priority} for t in tasks_done]

            # Pending tasks
            tasks_pending = db.query(Task).filter(
                Task.status != "done",
                Task.bucket.in_(["daily", "weekly"]),
            ).all()
            tasks_pending_data = [{"title": t.title, "bucket": t.bucket} for t in tasks_pending]

            # Brain dumps today
            dumps = db.query(BrainDump).filter(
                BrainDump.created_at.like(f"{date_str}%"),
                BrainDump.source != "journal",
            ).all()
            dump_data = [{"preview": d.raw_text[:80], "items": d.items_extracted} for d in dumps]

            # Journal entries today
            journals = db.query(BrainDump).filter(
                BrainDump.created_at.like(f"{date_str}%"),
                BrainDump.source == "journal",
            ).all()
            journal_data = [{"preview": j.raw_text[:80]} for j in journals]

            # New wiki pages today
            wiki_new = db.query(WikiPage).filter(
                WikiPage.created_at.like(f"{date_str}%"),
            ).all()
            wiki_data = [{"concept": p.concept, "folder": p.folder} for p in wiki_new]

        return {
            "tasks_completed": tasks_done_data,
            "tasks_pending": tasks_pending_data,
            "brain_dumps": dump_data,
            "journal_entries": journal_data,
            "wiki_pages_new": wiki_data,
        }

    def _build_context(self, activity: dict, date_str: str) -> str:
        parts = [f"Date: {date_str}"]

        if activity["tasks_completed"]:
            parts.append("Completed tasks:\n" + "\n".join(
                f"- [{t['priority']}] {t['title']}" for t in activity["tasks_completed"]
            ))

        if activity["tasks_pending"]:
            parts.append("Still pending:\n" + "\n".join(
                f"- [{t['bucket']}] {t['title']}" for t in activity["tasks_pending"][:8]
            ))

        if activity["brain_dumps"]:
            parts.append("Brain dumps today:\n" + "\n".join(
                f"- {d['preview']} ({d['items']} items)" for d in activity["brain_dumps"]
            ))

        if activity["journal_entries"]:
            parts.append("Journal entries:\n" + "\n".join(
                f"- {j['preview']}" for j in activity["journal_entries"]
            ))

        if activity["wiki_pages_new"]:
            parts.append("New wiki pages compiled:\n" + "\n".join(
                f"- [[{p['concept']}]] ({p['folder']})" for p in activity["wiki_pages_new"]
            ))

        return "\n\n".join(parts)

    def _fallback_review(self, activity: dict, date_str: str) -> str:
        """Plain text review when LLM unavailable."""
        done = len(activity["tasks_completed"])
        pending = len(activity["tasks_pending"])
        dumps = len(activity["brain_dumps"])
        wiki = len(activity["wiki_pages_new"])
        return (
            f"### Summary\n"
            f"- Tasks completed: {done}\n"
            f"- Tasks pending: {pending}\n"
            f"- Brain dumps: {dumps}\n"
            f"- Wiki pages compiled: {wiki}\n\n"
            f"### Tomorrow\n- Review pending tasks\n"
        )


_engine: DailyReviewEngine | None = None


def get_daily_review_engine() -> DailyReviewEngine:
    global _engine
    if _engine is None:
        _engine = DailyReviewEngine()
    return _engine
