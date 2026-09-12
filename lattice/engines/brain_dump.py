import uuid
import json
from datetime import datetime
from sqlalchemy.orm import Session

from config.prompts import BRAIN_DUMP_SYSTEM, BRAIN_DUMP_USER
from storage.models import Task, BrainDump, Intent
from storage.database import get_db
from engines.vault_writer import get_vault_writer
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("engines.brain_dump")


class BrainDumpEngine:
    def __init__(self):
        self.llm = get_llm()
        self.vault = get_vault_writer()

    async def process(self, raw_text: str, source: str = "desktop") -> dict:
        log.info(f"Processing brain dump ({len(raw_text)} chars) from {source}")

        prompt = BRAIN_DUMP_USER.format(raw_text=raw_text)
        try:
            result = await self.llm.complete_json(prompt, system=BRAIN_DUMP_SYSTEM)
        except Exception as e:
            log.error(f"Brain dump LLM failed: {e}")
            return {"error": str(e), "raw_text": raw_text}

        tasks_created = []
        questions_filed = []
        ideas_filed = []
        references_added = []
        fleeting_saved = []
        intents_filed = []

        now = datetime.utcnow().isoformat()
        dump_id = str(uuid.uuid4())

        with get_db() as db:
            # Tasks
            for item in result.get("tasks", []):
                task_id = str(uuid.uuid4())
                task = Task(
                    id=task_id,
                    title=item.get("title", "Untitled task"),
                    bucket=item.get("scope", "daily"),
                    priority=item.get("priority", "medium"),
                    status="inbox",
                    topic=item.get("topic"),
                    deadline=item.get("deadline"),
                    source=f"brain-dump:{dump_id[:8]}",
                    tags=json.dumps([]),
                    domain="personal" if item.get("topic") == "personal" else "academic",
                    created_at=now,
                    updated_at=now,
                )
                db.add(task)
                task_dict = {
                    "id": task_id,
                    "title": task.title,
                    "bucket": task.bucket,
                    "priority": task.priority,
                    "topic": task.topic,
                    "deadline": task.deadline,
                    "source": task.source,
                    "domain": task.domain,
                    "status": task.status,
                    "tags": [],
                    "created_at": now,
                }
                try:
                    note_path = self.vault.write_task_note(task_dict)
                    task.vault_note_path = note_path
                except Exception as e:
                    log.warning(f"Vault write failed for task: {e}")
                tasks_created.append({"title": task.title, "bucket": task.bucket, "priority": task.priority})

            # Questions
            for item in result.get("questions", []):
                try:
                    path = self.vault.append_question(item)
                    questions_filed.append({"text": item["text"], "topic": item.get("topic"), "path": path})
                except Exception as e:
                    log.warning(f"Question write failed: {e}")

            # Ideas
            for item in result.get("ideas", []):
                try:
                    path = self.vault.append_idea(item)
                    ideas_filed.append({"text": item["text"], "topic": item.get("topic"), "path": path})
                except Exception as e:
                    log.warning(f"Idea write failed: {e}")

            # References
            for item in result.get("references", []):
                try:
                    path = self.vault.append_reading_list(item)
                    references_added.append({"title": item["title"], "type": item.get("type"), "action": item.get("action")})
                except Exception as e:
                    log.warning(f"Reference write failed: {e}")

            # Fleeting
            for item in result.get("fleeting", []):
                try:
                    path = self.vault.append_fleeting(item)
                    fleeting_saved.append(item["text"])
                except Exception as e:
                    log.warning(f"Fleeting write failed: {e}")

            # Intents — commitments the scheduled planner will turn into a Project + vault plan
            for item in result.get("intents", []):
                if not item.get("title") or not item.get("text"):
                    continue
                intent = Intent(
                    id=str(uuid.uuid4()),
                    title=item["title"],
                    raw_text=item["text"],
                    topic=item.get("topic"),
                    brain_dump_id=dump_id,
                    status="pending",
                    created_at=now,
                )
                db.add(intent)
                intents_filed.append({"title": intent.title, "text": intent.raw_text, "topic": intent.topic})

            # Store dump record
            total_items = (
                len(tasks_created) + len(questions_filed) +
                len(ideas_filed) + len(references_added) + len(fleeting_saved) +
                len(intents_filed)
            )
            dump_record = BrainDump(
                id=dump_id,
                raw_text=raw_text,
                processed_json=json.dumps(result),
                items_extracted=total_items,
                source=source,
                created_at=now,
            )
            db.add(dump_record)

        log.info(f"Brain dump processed: {total_items} items extracted")

        return {
            "dump_id": dump_id,
            "total_items": total_items,
            "tasks": tasks_created,
            "questions": questions_filed,
            "ideas": ideas_filed,
            "references": references_added,
            "fleeting": fleeting_saved,
            "intents": intents_filed,
        }


_engine: BrainDumpEngine | None = None


def get_brain_dump_engine() -> BrainDumpEngine:
    global _engine
    if _engine is None:
        _engine = BrainDumpEngine()
    return _engine
