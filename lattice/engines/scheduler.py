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

JOB_TIMEOUT = 300.0  # 5 min max per scheduled job


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

        self._scheduler.add_job(
            self._checkin_job,
            IntervalTrigger(minutes=s.checkin_interval_minutes),
            id="checkin",
            replace_existing=True,
        )

        review_h, review_m = s.daily_review_time.split(":")
        self._scheduler.add_job(
            self._daily_review_job,
            CronTrigger(hour=int(review_h), minute=int(review_m)),
            id="daily_review",
            replace_existing=True,
        )

        maint_h, maint_m = s.nightly_maintenance_time.split(":")
        self._scheduler.add_job(
            self._nightly_maintenance_job,
            CronTrigger(hour=int(maint_h), minute=int(maint_m)),
            id="nightly_maintenance",
            replace_existing=True,
        )

        self._scheduler.add_job(
            self._git_commit_job,
            IntervalTrigger(hours=1),
            id="git_commit",
            replace_existing=True,
        )

        self._scheduler.add_job(
            self._intent_planning_job,
            IntervalTrigger(minutes=s.intent_planning_interval_minutes),
            id="intent_planning",
            replace_existing=True,
        )

        log.info(f"Jobs configured: checkin/{s.checkin_interval_minutes}min, "
                 f"daily-review/{s.daily_review_time}, "
                 f"maintenance/{s.nightly_maintenance_time}, "
                 f"intent-planning/{s.intent_planning_interval_minutes}min")

    async def _checkin_job(self):
        now = datetime.now()
        if not (self.settings.work_start <= now.strftime("%H:%M") <= self.settings.work_end):
            log.debug(f"Check-in skipped at {now.strftime('%H:%M')} — outside work hours")
            return
        log.info(f"Check-in ping at {now.strftime('%H:%M')}")
        try:
            _send_notification(
                "Lattice Check-in",
                f"[{now.strftime('%H:%M')}] What are you working on? Drop a brain dump!",
            )
        except Exception as e:
            log.warning(f"Notification failed: {e}")

    async def _daily_review_job(self):
        log.info("Daily review job starting")
        try:
            from engines.daily_review import get_daily_review_engine
            result = await asyncio.wait_for(
                get_daily_review_engine().generate(),
                timeout=JOB_TIMEOUT,
            )
            _send_notification(
                "Lattice Daily Review",
                f"Daily review ready: {result['tasks_completed']} tasks done today.",
            )
            from engines.telegram_bot import send_telegram
            await send_telegram(f"Daily Review — {result['date']}\n\n{result['review_text']}")
            log.info(f"Daily review complete: {result}")
        except asyncio.TimeoutError:
            log.error(f"Daily review timed out after {JOB_TIMEOUT}s")
        except Exception as e:
            log.error(f"Daily review job failed: {e}")

    async def _nightly_maintenance_job(self):
        log.info("Nightly maintenance starting")
        try:
            from engines.graph_builder import get_graph_builder

            async def _rebuild():
                return await asyncio.to_thread(get_graph_builder().build_all)

            result = await asyncio.wait_for(_rebuild(), timeout=JOB_TIMEOUT)
            log.info(f"Nightly graph rebuild: {result}")

            if self.settings.self_improve_enabled:
                from engines.self_improve import get_self_improve_engine

                async def _health_check():
                    return await asyncio.to_thread(get_self_improve_engine().run_full_check)

                health = await asyncio.wait_for(_health_check(), timeout=JOB_TIMEOUT)
                log.info(f"Vault health check: {health}")

            await self._git_commit_job()
            log.info("Nightly maintenance complete")
        except asyncio.TimeoutError:
            log.error(f"Nightly maintenance timed out after {JOB_TIMEOUT}s")
        except Exception as e:
            log.error(f"Nightly maintenance failed: {e}")

    async def _intent_planning_job(self):
        log.info("Intent planning sweep starting")
        try:
            from engines.intent_planner import get_intent_planner
            result = await asyncio.wait_for(
                get_intent_planner().plan_pending(),
                timeout=JOB_TIMEOUT,
            )
            if result["planned"]:
                log.info(f"Intent planning: {result['planned']} plan(s) created")
                _send_notification(
                    "Lattice",
                    f"{result['planned']} new plan(s) ready — check Projects.",
                )
        except asyncio.TimeoutError:
            log.error(f"Intent planning timed out after {JOB_TIMEOUT}s")
        except Exception as e:
            log.error(f"Intent planning failed: {e}")

    async def _git_commit_job(self):
        try:
            from engines.git_engine import get_git_engine
            result = await asyncio.to_thread(get_git_engine().auto_commit)
            if not result.get("skipped"):
                log.info(f"Auto git commit: {result.get('sha')} — {result.get('message')}")
        except Exception as e:
            log.warning(f"Git auto-commit failed: {e}")

    def get_jobs(self) -> list[dict]:
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
