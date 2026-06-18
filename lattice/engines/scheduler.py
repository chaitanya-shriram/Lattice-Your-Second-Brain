"""
APScheduler: cron jobs for periodic Lattice tasks.
- Check-in every 2h during work hours
- Daily review at DAILY_REVIEW_TIME
- Nightly maintenance at NIGHTLY_MAINTENANCE_TIME
"""
import asyncio
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from config.settings import get_settings
from utils.logger import get_logger

log = get_logger("engines.scheduler")


class LatticeScheduler:
    def __init__(self):
        self.settings = get_settings()
        self._scheduler = AsyncIOScheduler(timezone="UTC")
        self._running = False

    def start(self):
        if self._running:
            return
        self._configure_jobs()
        self._scheduler.start()
        self._running = True
        log.info("Scheduler started")

    def stop(self):
        if self._running:
            self._scheduler.shutdown(wait=False)
            self._running = False
            log.info("Scheduler stopped")

    def _configure_jobs(self):
        s = self.settings

        # [1] Check-in every N minutes during work hours
        work_start_h = int(s.work_start.split(":")[0])
        work_end_h = int(s.work_end.split(":")[0])

        self._scheduler.add_job(
            self._checkin_job,
            IntervalTrigger(minutes=s.checkin_interval_minutes),
            id="checkin",
            replace_existing=True,
        )

        # [2] Daily review
        review_h, review_m = s.daily_review_time.split(":")
        self._scheduler.add_job(
            self._daily_review_job,
            CronTrigger(hour=int(review_h), minute=int(review_m)),
            id="daily_review",
            replace_existing=True,
        )

        # [3] Nightly maintenance
        maint_h, maint_m = s.nightly_maintenance_time.split(":")
        self._scheduler.add_job(
            self._nightly_maintenance_job,
            CronTrigger(hour=int(maint_h), minute=int(maint_m)),
            id="nightly_maintenance",
            replace_existing=True,
        )

        # [4] Auto git commit every hour
        self._scheduler.add_job(
            self._git_commit_job,
            IntervalTrigger(hours=1),
            id="git_commit",
            replace_existing=True,
        )

        log.info(f"Jobs configured: checkin/{s.checkin_interval_minutes}min, "
                 f"daily-review/{s.daily_review_time}, "
                 f"maintenance/{s.nightly_maintenance_time}")

    async def _checkin_job(self):
        """Nudge notification: what are you working on?"""
        now = datetime.now()
        log.info(f"Check-in ping at {now.strftime('%H:%M')}")

        try:
            _send_notification(
                "Lattice Check-in",
                f"[{now.strftime('%H:%M')}] What are you working on? Drop a brain dump!",
            )
        except Exception as e:
            log.warning(f"Notification failed: {e}")

    async def _daily_review_job(self):
        """Generate daily review with LLM synthesis."""
        log.info("Daily review job starting")
        try:
            from engines.daily_review import get_daily_review_engine
            result = await get_daily_review_engine().generate()
            _send_notification(
                "Lattice Daily Review",
                f"Daily review ready: {result['tasks_completed']} tasks done today.",
            )
            log.info(f"Daily review complete: {result}")
        except Exception as e:
            log.error(f"Daily review job failed: {e}")

    async def _nightly_maintenance_job(self):
        """Run graph rebuild + git commit + wiki health check."""
        log.info("Nightly maintenance starting")
        try:
            # 1. Graph rebuild
            from engines.graph_builder import get_graph_builder
            result = get_graph_builder().build_all()
            log.info(f"Nightly graph rebuild: {result}")

            # 2. Git auto-commit
            await self._git_commit_job()

            log.info("Nightly maintenance complete")
        except Exception as e:
            log.error(f"Nightly maintenance failed: {e}")

    async def _git_commit_job(self):
        """Auto-commit vault changes to git."""
        try:
            from engines.git_engine import get_git_engine
            result = get_git_engine().auto_commit()
            if not result.get("skipped"):
                log.info(f"Auto git commit: {result.get('sha')} — {result.get('message')}")
        except Exception as e:
            log.warning(f"Git auto-commit failed: {e}")

    def get_jobs(self) -> list[dict]:
        """Return list of scheduled jobs for inspection."""
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
            })
        return jobs


def _send_notification(title: str, message: str):
    """Send Windows desktop notification via plyer."""
    try:
        from plyer import notification
        notification.notify(
            title=title,
            message=message,
            app_name="Lattice",
            timeout=8,
        )
    except ImportError:
        log.debug(f"Notification (plyer unavailable): [{title}] {message}")
    except Exception as e:
        log.debug(f"Notification failed: {e}")


_scheduler: LatticeScheduler | None = None


def get_scheduler() -> LatticeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = LatticeScheduler()
    return _scheduler
