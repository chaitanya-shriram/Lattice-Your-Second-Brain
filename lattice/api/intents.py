from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import Intent

router = APIRouter()


def _intent_to_dict(i: Intent) -> dict:
    return {
        "id": i.id,
        "title": i.title,
        "raw_text": i.raw_text,
        "topic": i.topic,
        "status": i.status,
        "project_id": i.project_id,
        "vault_note_path": i.vault_note_path,
        "error": i.error,
        "created_at": i.created_at,
        "planned_at": i.planned_at,
    }


@router.get("/")
async def list_intents(db: Session = Depends(get_db_dependency)):
    intents = db.query(Intent).order_by(Intent.created_at.desc()).limit(50).all()
    return [_intent_to_dict(i) for i in intents]


@router.post("/run-now")
async def run_now():
    """Manually trigger the intent-planning sweep instead of waiting for the schedule."""
    from engines.intent_planner import get_intent_planner
    return await get_intent_planner().plan_pending()
