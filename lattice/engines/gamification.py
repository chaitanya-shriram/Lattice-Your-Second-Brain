"""
Gamification Engine: XP system, 4 streak types, achievements, weekly report.
All state stored in GamificationStats (singleton) + XPLog + Achievement tables.
"""
import uuid
import json
from datetime import datetime, date, timedelta

from storage.database import get_db
from storage.models import GamificationStats, XPLog, Achievement
from utils.logger import get_logger

log = get_logger("engines.gamification")

XP_TABLE = {
    "brain_dump": 10,
    "task_created": 5,
    "task_completed": 20,
    "question_filed": 8,
    "file_ingested": 15,
    "wiki_compiled": 25,
    "journal_entry": 12,
    "daily_review": 30,
    "streak_bonus": 50,
}

LEVELS = [
    (0, "Apprentice"),
    (100, "Seeker"),
    (300, "Learner"),
    (600, "Scholar"),
    (1000, "Researcher"),
    (1500, "Analyst"),
    (2500, "Expert"),
    (4000, "Master"),
    (6000, "Sage"),
    (10000, "Luminary"),
]

ACHIEVEMENTS = [
    ("first_dump", "First Capture", "Completed your first brain dump", 1, "brain_dump"),
    ("streak_7", "Week Streak", "Maintained a 7-day capture streak", 0, None),
    ("wiki_10", "Wiki Builder", "Compiled 10 wiki pages", 0, None),
    ("tasks_50", "Task Master", "Completed 50 tasks", 0, None),
    ("files_10", "Archivist", "Ingested 10 files", 0, None),
    ("scholar", "Scholar Level", "Reached Scholar level (600 XP)", 0, None),
]


class GamificationEngine:
    def __init__(self):
        self._stats_id = "singleton"

    def _get_stats(self, db) -> GamificationStats:
        stats = db.query(GamificationStats).filter(
            GamificationStats.id == self._stats_id
        ).first()
        if not stats:
            now = datetime.utcnow().isoformat()
            stats = GamificationStats(id=self._stats_id, updated_at=now)
            db.add(stats)
            db.flush()
        return stats

    def award_xp(self, action: str, context: str = "") -> dict:
        """Award XP for an action and update streaks."""
        xp = XP_TABLE.get(action, 0)
        if xp == 0:
            return {"action": action, "xp": 0, "skipped": True}

        now = datetime.utcnow().isoformat()
        today = date.today().isoformat()

        new_total_xp = 0
        new_level_name = ""
        level_up = False

        with get_db() as db:
            stats = self._get_stats(db)
            old_level = self._xp_to_level(stats.total_xp or 0)

            stats.total_xp = (stats.total_xp or 0) + xp
            new_total_xp = stats.total_xp
            new_level_name = self._xp_to_level(new_total_xp)
            level_up = old_level != new_level_name

            # Update counters
            if action == "brain_dump":
                stats.total_brain_dumps = (stats.total_brain_dumps or 0) + 1
                stats.last_capture_date = today
            elif action == "task_completed":
                stats.total_tasks_completed = (stats.total_tasks_completed or 0) + 1
                stats.last_task_date = today
            elif action == "file_ingested":
                stats.total_files_ingested = (stats.total_files_ingested or 0) + 1
                stats.last_study_date = today
            elif action == "wiki_compiled":
                stats.total_wiki_pages_compiled = (stats.total_wiki_pages_compiled or 0) + 1
            elif action == "question_filed":
                stats.total_questions_filed = (stats.total_questions_filed or 0) + 1
                stats.last_question_date = today
            elif action == "journal_entry":
                stats.total_journal_entries = (stats.total_journal_entries or 0) + 1
            elif action == "task_created":
                stats.total_tasks_created = (stats.total_tasks_created or 0) + 1

            # Update level number
            level_num = 0
            for i, (threshold, _) in enumerate(LEVELS):
                if new_total_xp >= threshold:
                    level_num = i
            stats.current_level = level_num
            stats.updated_at = now

            # Log XP
            xp_entry = XPLog(
                id=str(uuid.uuid4()),
                action=action,
                xp_earned=xp,
                description=context[:200],
                earned_at=now,
            )
            db.add(xp_entry)

        # Check achievements
        self._check_achievements()

        result = {
            "action": action,
            "xp_earned": xp,
            "total_xp": new_total_xp,
            "level": new_level_name,
            "level_up": level_up,
        }
        log.debug(f"XP awarded: +{xp} for {action}")
        return result

    def get_stats(self) -> dict:
        """Return full gamification stats."""
        with get_db() as db:
            stats = self._get_stats(db)
            total_xp = stats.total_xp or 0
            level_num = stats.current_level or 0
            level_name = LEVELS[min(level_num, len(LEVELS) - 1)][1]
            next_level = LEVELS[min(level_num + 1, len(LEVELS) - 1)]

            xp_to_next = max(0, next_level[0] - total_xp)

            return {
                "total_xp": total_xp,
                "current_level": level_num,
                "level_name": level_name,
                "xp_to_next_level": xp_to_next,
                "capture_streak": stats.capture_streak or 0,
                "study_streak": stats.study_streak or 0,
                "question_streak": stats.question_streak or 0,
                "task_streak": stats.task_streak or 0,
                "best_capture_streak": stats.best_capture_streak or 0,
                "total_brain_dumps": stats.total_brain_dumps or 0,
                "total_tasks_completed": stats.total_tasks_completed or 0,
                "total_files_ingested": stats.total_files_ingested or 0,
                "total_wiki_pages_compiled": stats.total_wiki_pages_compiled or 0,
                "total_journal_entries": stats.total_journal_entries or 0,
            }

    def get_xp_log(self, limit: int = 20) -> list[dict]:
        with get_db() as db:
            entries = (
                db.query(XPLog)
                .order_by(XPLog.earned_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "action": e.action,
                    "xp_earned": e.xp_earned,
                    "description": e.description,
                    "earned_at": e.earned_at,
                }
                for e in entries
            ]

    def get_achievements(self) -> list[dict]:
        with get_db() as db:
            achievements = db.query(Achievement).all()
            return [
                {
                    "id": a.id,
                    "badge_id": a.badge_id,
                    "name": a.badge_name,
                    "xp_awarded": a.xp_awarded,
                    "unlocked_at": a.unlocked_at,
                }
                for a in achievements
            ]

    def _check_achievements(self):
        """Check and award any newly earned achievements."""
        with get_db() as db:
            stats = self._get_stats(db)
            existing = {a.id for a in db.query(Achievement).all()}
            now = datetime.utcnow().isoformat()

            def _award(ach_id, name, description, xp_bonus=0):
                if ach_id not in existing:
                    db.add(Achievement(
                        id=ach_id,
                        badge_id=ach_id,
                        badge_name=name,
                        xp_awarded=xp_bonus,
                        unlocked_at=now,
                    ))
                    existing.add(ach_id)
                    log.info(f"Achievement unlocked: {name}")

            if (stats.total_brain_dumps or 0) >= 1:
                _award("first_dump", "First Capture", "Completed your first brain dump", 0)
            if (stats.capture_streak or 0) >= 7:
                _award("streak_7", "Week Streak", "7-day capture streak", 50)
            if (stats.total_wiki_pages_compiled or 0) >= 10:
                _award("wiki_10", "Wiki Builder", "Compiled 10 wiki pages", 100)
            if (stats.total_tasks_completed or 0) >= 50:
                _award("tasks_50", "Task Master", "Completed 50 tasks", 200)
            if (stats.total_files_ingested or 0) >= 10:
                _award("files_10", "Archivist", "Ingested 10 files", 100)
            if (stats.total_xp or 0) >= 600:
                _award("scholar", "Scholar Level", "Reached 600 XP", 0)

    def _xp_to_level(self, xp: int) -> str:
        level = LEVELS[0][1]
        for threshold, name in LEVELS:
            if xp >= threshold:
                level = name
        return level

    def generate_weekly_report(self) -> dict:
        """Generate a weekly progress summary."""
        week_ago = (date.today() - timedelta(days=7)).isoformat()

        with get_db() as db:
            stats = self._get_stats(db)
            total_xp = stats.total_xp or 0
            streaks = {
                "capture": stats.capture_streak or 0,
                "study": stats.study_streak or 0,
                "question": stats.question_streak or 0,
                "task": stats.task_streak or 0,
            }
            weekly_logs = (
                db.query(XPLog)
                .filter(XPLog.earned_at >= week_ago)
                .all()
            )
            weekly_xp_total = sum(e.xp_earned for e in weekly_logs)
            actions = {}
            for e in weekly_logs:
                actions[e.action] = actions.get(e.action, 0) + 1

        return {
            "period": "last 7 days",
            "xp_earned": weekly_xp_total,
            "total_xp": total_xp,
            "level": self._xp_to_level(total_xp),
            "actions": actions,
            "streaks": streaks,
        }


_engine: GamificationEngine | None = None


def get_gamification_engine() -> GamificationEngine:
    global _engine
    if _engine is None:
        _engine = GamificationEngine()
    return _engine
