import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import Task

router = APIRouter()


class TaskCreate(BaseModel):
    title: str
    bucket: str = "daily"
    priority: str = "medium"
    description: Optional[str] = None
    topic: Optional[str] = None
    deadline: Optional[str] = None
    estimated_minutes: Optional[int] = None
    tags: Optional[list[str]] = None
    domain: str = "academic"
    source: str = "desktop"


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    bucket: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    topic: Optional[str] = None
    deadline: Optional[str] = None
    estimated_minutes: Optional[int] = None
    actual_minutes: Optional[int] = None
    tags: Optional[list[str]] = None
    domain: Optional[str] = None


def _task_to_dict(t: Task) -> dict:
    import json
    try:
        tags = json.loads(t.tags) if t.tags else []
    except (json.JSONDecodeError, ValueError):
        tags = []
    return {
        "id": t.id,
        "title": t.title,
        "description": t.description,
        "bucket": t.bucket,
        "priority": t.priority,
        "status": t.status,
        "topic": t.topic,
        "deadline": t.deadline,
        "due_date": t.deadline,  # alias for frontend
        "scheduled_date": t.scheduled_date,
        "estimated_minutes": t.estimated_minutes,
        "actual_minutes": t.actual_minutes,
        "tags": tags,
        "domain": t.domain,
        "source": t.source,
        "vault_note_path": t.vault_note_path,
        "created_at": t.created_at,
        "updated_at": t.updated_at,
        "completed_at": t.completed_at,
    }


@router.get("/")
async def list_tasks(
    bucket: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    domain: Optional[str] = Query(None),
    topic: Optional[str] = Query(None),
    db: Session = Depends(get_db_dependency),
):
    import json
    q = db.query(Task)
    if bucket:
        q = q.filter(Task.bucket == bucket)
    if status:
        q = q.filter(Task.status == status)
    if domain:
        q = q.filter(Task.domain == domain)
    if topic:
        q = q.filter(Task.topic == topic)
    tasks = q.order_by(Task.created_at.desc()).all()
    return [_task_to_dict(t) for t in tasks]


@router.post("/", status_code=201)
async def create_task(body: TaskCreate, db: Session = Depends(get_db_dependency)):
    import json
    now = datetime.utcnow().isoformat()
    task = Task(
        id=str(uuid.uuid4()),
        title=body.title,
        bucket=body.bucket,
        priority=body.priority,
        status="inbox",
        description=body.description,
        topic=body.topic,
        deadline=body.deadline,
        estimated_minutes=body.estimated_minutes,
        tags=json.dumps(body.tags or []),
        domain=body.domain,
        source=body.source,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.get("/{task_id}")
async def get_task(task_id: str, db: Session = Depends(get_db_dependency)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_dict(task)


@router.patch("/{task_id}")
async def update_task(
    task_id: str,
    body: TaskUpdate,
    db: Session = Depends(get_db_dependency),
):
    import json
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    for field, value in body.model_dump(exclude_none=True).items():
        if field == "tags":
            setattr(task, "tags", json.dumps(value))
        else:
            setattr(task, field, value)

    task.updated_at = datetime.utcnow().isoformat()

    if body.status == "done" and not task.completed_at:
        task.completed_at = datetime.utcnow().isoformat()

    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: str, db: Session = Depends(get_db_dependency)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, db: Session = Depends(get_db_dependency)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    now = datetime.utcnow().isoformat()
    task.status = "done"
    task.completed_at = now
    task.updated_at = now
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.get("/stats/summary")
async def task_stats(db: Session = Depends(get_db_dependency)):
    from storage.models import File as FileModel, WikiPage

    today = datetime.utcnow().date().isoformat()
    buckets = ["daily", "weekly", "long-term", "someday", "recurring", "waiting"]
    by_bucket = {}
    for b in buckets:
        by_bucket[b] = {
            "total": db.query(Task).filter(Task.bucket == b).count(),
            "done": db.query(Task).filter(Task.bucket == b, Task.status == "done").count(),
            "active": db.query(Task).filter(Task.bucket == b, Task.status != "done").count(),
        }

    return {
        "by_bucket": by_bucket,
        "pending": db.query(Task).filter(Task.status != "done").count(),
        "completed_today": db.query(Task).filter(
            Task.status == "done",
            Task.completed_at.like(f"{today}%"),
        ).count(),
        "files": db.query(FileModel).count(),
        "wiki_pages": db.query(WikiPage).count(),
    }
