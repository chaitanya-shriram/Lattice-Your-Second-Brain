"""
Turns stated commitments ("I'm going to build X") into an actual plan:
a Project (with sections + tasks) and a vault note laying out the plan.
Runs periodically off the scheduler — see engines/scheduler.py.
"""
import asyncio
from datetime import datetime
from sqlalchemy import func

from config.prompts import INTENT_PLAN_SYSTEM, INTENT_PLAN_USER
from storage.models import Intent, Project, ProjectSection, ProjectTask
from storage.database import get_db
from engines.vault_writer import get_vault_writer
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("engines.intent_planner")

PROJECT_COLORS = ["#796EFF", "#e8384f", "#f2a100", "#37c5ab", "#4186e0", "#e362e3"]


def _next_position(db, model, **filters) -> float:
    q = db.query(func.max(model.position))
    for k, v in filters.items():
        q = q.filter(getattr(model, k) == v)
    max_pos = q.scalar()
    return (max_pos or 0) + 1


class IntentPlannerEngine:
    def __init__(self):
        self.llm = get_llm()
        self.vault = get_vault_writer()
        # Manual "run-now" and the scheduled sweep both grab all pending
        # intents up front — without this, an overlapping run would plan
        # the same intent twice (duplicate project + vault note).
        self._lock = asyncio.Lock()

    async def plan_pending(self) -> dict:
        if self._lock.locked():
            log.info("Intent planning already in progress, skipping overlapping run")
            return {"planned": 0, "items": [], "skipped": True}

        async with self._lock:
            with get_db() as db:
                pending = db.query(Intent).filter(Intent.status == "pending").all()
                items = [
                    {"id": i.id, "title": i.title, "text": i.raw_text, "topic": i.topic}
                    for i in pending
                ]

            planned = []
            for item in items:
                try:
                    planned.append(await self._plan_one(item))
                except Exception as e:
                    log.error(f"Planning failed for intent {item['id']} ({item['title']!r}): {e}")
                    with get_db() as db:
                        intent = db.get(Intent, item["id"])
                        if intent:
                            intent.status = "failed"
                            intent.error = str(e)

            return {"planned": len(planned), "items": planned}

    async def _plan_one(self, item: dict) -> dict:
        prompt = INTENT_PLAN_USER.format(text=item["text"], title=item["title"])
        plan = await self.llm.complete_json(prompt, system=INTENT_PLAN_SYSTEM)

        now = datetime.utcnow().isoformat()
        with get_db() as db:
            project = Project(
                name=item["title"],
                color=PROJECT_COLORS[db.query(Project).count() % len(PROJECT_COLORS)],
                position=_next_position(db, Project),
                description=plan.get("description", ""),
                created_at=now,
            )
            db.add(project)
            db.flush()

            section_ids = {}
            for sname in plan.get("sections") or []:
                sec = ProjectSection(
                    project_id=project.id, name=sname,
                    position=_next_position(db, ProjectSection, project_id=project.id),
                )
                db.add(sec)
                db.flush()
                section_ids[sname] = sec.id

            checklist = []
            for t in plan.get("tasks") or []:
                if not t.get("name"):
                    continue
                section_id = section_ids.get(t.get("section"))
                db.add(ProjectTask(
                    project_id=project.id, section_id=section_id, name=t["name"],
                    priority=t.get("priority"), due_date=t.get("due_date"),
                    position=_next_position(db, ProjectTask, project_id=project.id),
                    created_at=now,
                ))
                checklist.append({"name": t["name"], "section": t.get("section")})

            vault_note_path = self.vault.write_intent_plan({
                "title": item["title"],
                "raw_text": item["text"],
                "description": plan.get("description", ""),
                "checklist": checklist,
                "notes": plan.get("notes", ""),
                "project_id": project.id,
            })

            intent = db.get(Intent, item["id"])
            intent.status = "planned"
            intent.project_id = project.id
            intent.vault_note_path = vault_note_path
            intent.planned_at = now

            result = {
                "id": item["id"], "title": item["title"],
                "project_id": project.id, "vault_note_path": vault_note_path,
            }

        log.info(f"Planned intent {item['id']!r}: project #{result['project_id']}, note {vault_note_path}")
        return result


_engine: IntentPlannerEngine | None = None


def get_intent_planner() -> IntentPlannerEngine:
    global _engine
    if _engine is None:
        _engine = IntentPlannerEngine()
    return _engine
