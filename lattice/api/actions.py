from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import ActionLog

router = APIRouter()


@router.get("/")
def list_actions(
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db_dependency),
):
    logs = (
        db.query(ActionLog)
        .order_by(ActionLog.executed_at.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": l.id,
            "action_type": l.action_type,
            "status": l.status,
            "executed_at": l.executed_at,
        }
        for l in logs
    ]
