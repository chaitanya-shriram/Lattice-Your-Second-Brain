import json
import re
import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from storage.database import get_db_dependency
from storage.models import Project, ProjectSection, ProjectTask, TaskDependency, ProjectUpdate, Task, BrainDump
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("api.projects")

router = APIRouter()

PROJECT_COLORS = ["#796EFF", "#e8384f", "#f2a100", "#37c5ab", "#4186e0", "#e362e3"]


# ── serialization ──────────────────────────────────────────────────────

def _project_to_dict(p: Project, pending_count: int | None = None) -> dict:
    d = {
        "id": p.id,
        "name": p.name,
        "color": p.color,
        "position": p.position,
        "description": p.description,
        "collaborators": p.collaborators,
        "is_inbox": p.is_inbox,
        "created_at": p.created_at,
    }
    if pending_count is not None:
        d["pending_count"] = pending_count
    return d


def _section_to_dict(s: ProjectSection) -> dict:
    return {"id": s.id, "project_id": s.project_id, "name": s.name, "position": s.position}


def _task_to_dict(t: ProjectTask, blocked: bool = False, depends_on: list[int] | None = None) -> dict:
    return {
        "id": t.id,
        "project_id": t.project_id,
        "section_id": t.section_id,
        "parent_id": t.parent_id,
        "name": t.name,
        "notes": t.notes,
        "due_date": t.due_date,
        "completed": t.completed,
        "position": t.position,
        "is_milestone": t.is_milestone,
        "priority": t.priority,
        "effort": t.effort,
        "tags": t.tags,
        "created_at": t.created_at,
        "blocked": blocked,
        "depends_on": depends_on or [],
    }


def _update_to_dict(u: ProjectUpdate) -> dict:
    return {
        "id": u.id,
        "project_id": u.project_id,
        "status": u.status,
        "body": u.body,
        "created_at": u.created_at,
    }


async def _generate_description(name: str, task_names: list[str]) -> str:
    """Best-effort 10-20 word project description. Empty string if LLM unavailable."""
    try:
        prompt = f"Project name: {name}\n"
        if task_names:
            prompt += "Sample tasks: " + ", ".join(task_names[:8]) + "\n"
        prompt += "Write a 10-20 word description of this project. Return only the description text, no quotes."
        text = await get_llm().complete(prompt, system="You write terse, concrete project descriptions.")
        return text.strip().strip('"')
    except Exception as e:
        log.warning(f"Description generation failed: {e}")
        return ""


def _next_position(db: Session, model, **filters) -> float:
    q = db.query(func.max(model.position))
    for k, v in filters.items():
        q = q.filter(getattr(model, k) == v)
    max_pos = q.scalar()
    return (max_pos or 0) + 1


# ── request bodies ────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    color: Optional[str] = None


class ProjectUpdateBody(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    description: Optional[str] = None
    collaborators: Optional[str] = None


class SectionCreate(BaseModel):
    name: str


class TaskCreate(BaseModel):
    name: str
    section_id: Optional[int] = None
    parent_id: Optional[int] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None


class TaskUpdateBody(BaseModel):
    name: Optional[str] = None
    notes: Optional[str] = None
    due_date: Optional[str] = None
    completed: Optional[bool] = None
    section_id: Optional[int] = None
    parent_id: Optional[int] = None
    position: Optional[float] = None
    is_milestone: Optional[bool] = None
    priority: Optional[str] = None
    effort: Optional[int] = None
    tags: Optional[str] = None


class DependencyCreate(BaseModel):
    depends_on_id: int


class StatusUpdateCreate(BaseModel):
    status: str
    body: str = ""


# ── projects: list / home / my-tasks (must precede /{project_id}) ─────

@router.get("/")
async def list_projects(db: Session = Depends(get_db_dependency)):
    projects = db.query(Project).order_by(Project.position).all()
    out = []
    for p in projects:
        pending = db.query(ProjectTask).filter(
            ProjectTask.project_id == p.id,
            ProjectTask.parent_id.is_(None),
            ProjectTask.completed.is_(False),
        ).count()
        out.append(_project_to_dict(p, pending))
    return out


@router.get("/home")
async def home_board(db: Session = Depends(get_db_dependency)):
    projects = db.query(Project).order_by(Project.position).all()
    out = []
    for p in projects:
        top_level = db.query(ProjectTask).filter(
            ProjectTask.project_id == p.id, ProjectTask.parent_id.is_(None)
        ).all()
        done = sum(1 for t in top_level if t.completed)
        pending = [t for t in top_level if not t.completed]
        latest = (
            db.query(ProjectUpdate)
            .filter(ProjectUpdate.project_id == p.id)
            .order_by(ProjectUpdate.created_at.desc())
            .first()
        )
        out.append({
            **_project_to_dict(p),
            "done_count": done,
            "total_count": len(top_level),
            "pending_tasks": [
                {"id": t.id, "name": t.name, "due_date": t.due_date, "priority": t.priority}
                for t in sorted(pending, key=lambda t: (t.due_date is None, t.due_date or "", t.position))[:5]
            ],
            "latest_update": _update_to_dict(latest) if latest else None,
        })
    return out


@router.get("/my-tasks")
async def my_tasks(db: Session = Depends(get_db_dependency)):
    tasks = db.query(ProjectTask).filter(
        ProjectTask.parent_id.is_(None), ProjectTask.completed.is_(False)
    ).all()
    tasks.sort(key=lambda t: (t.due_date is None, t.due_date or "", t.position))
    project_map = {p.id: p for p in db.query(Project).all()}
    out = []
    for t in tasks:
        proj = project_map.get(t.project_id)
        d = _task_to_dict(t)
        d["project_name"] = proj.name if proj else None
        d["project_color"] = proj.color if proj else None
        out.append(d)
    return out


@router.post("/", status_code=201)
async def create_project(body: ProjectCreate, db: Session = Depends(get_db_dependency)):
    now = datetime.utcnow().isoformat()
    description = await _generate_description(body.name, [])
    project = Project(
        name=body.name,
        color=body.color or PROJECT_COLORS[0],
        position=_next_position(db, Project),
        description=description,
        created_at=now,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _project_to_dict(project)


# ── projects: single-item routes ───────────────────────────────────────

@router.get("/{project_id}")
async def get_project(project_id: int, db: Session = Depends(get_db_dependency)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_dict(project)


@router.get("/{project_id}/full")
async def get_project_full(project_id: int, db: Session = Depends(get_db_dependency)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    sections = db.query(ProjectSection).filter(
        ProjectSection.project_id == project_id
    ).order_by(ProjectSection.position).all()
    tasks = db.query(ProjectTask).filter(ProjectTask.project_id == project_id).all()
    updates = db.query(ProjectUpdate).filter(
        ProjectUpdate.project_id == project_id
    ).order_by(ProjectUpdate.created_at.desc()).all()

    task_ids = [t.id for t in tasks]
    deps = (
        db.query(TaskDependency).filter(TaskDependency.task_id.in_(task_ids)).all()
        if task_ids else []
    )
    deps_by_task: dict[int, list[int]] = {}
    for d in deps:
        deps_by_task.setdefault(d.task_id, []).append(d.depends_on_id)

    completed_ids = {t.id for t in tasks if t.completed}
    task_dicts = []
    for t in tasks:
        depends_on = deps_by_task.get(t.id, [])
        blocked = any(dep_id not in completed_ids for dep_id in depends_on)
        task_dicts.append(_task_to_dict(t, blocked=blocked, depends_on=depends_on))

    return {
        **_project_to_dict(project),
        "sections": [_section_to_dict(s) for s in sections],
        "tasks": task_dicts,
        "updates": [_update_to_dict(u) for u in updates],
    }


@router.patch("/{project_id}")
async def update_project(project_id: int, body: ProjectUpdateBody, db: Session = Depends(get_db_dependency)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return _project_to_dict(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: int, db: Session = Depends(get_db_dependency)):
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.is_inbox:
        raise HTTPException(status_code=400, detail="Cannot delete the Personal inbox project")
    db.delete(project)
    db.commit()


# ── sections ─────────────────────────────────────────────────────────

@router.post("/{project_id}/sections", status_code=201)
async def create_section(project_id: int, body: SectionCreate, db: Session = Depends(get_db_dependency)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    section = ProjectSection(
        project_id=project_id,
        name=body.name,
        position=_next_position(db, ProjectSection, project_id=project_id),
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return _section_to_dict(section)


@router.delete("/sections/{section_id}", status_code=204)
async def delete_section(section_id: int, db: Session = Depends(get_db_dependency)):
    section = db.get(ProjectSection, section_id)
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    # Unassign tasks rather than cascade-delete them
    db.query(ProjectTask).filter(ProjectTask.section_id == section_id).update({"section_id": None})
    db.delete(section)
    db.commit()


# ── tasks ────────────────────────────────────────────────────────────

@router.post("/{project_id}/tasks", status_code=201)
async def create_task(project_id: int, body: TaskCreate, db: Session = Depends(get_db_dependency)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    task = ProjectTask(
        project_id=project_id,
        section_id=body.section_id,
        parent_id=body.parent_id,
        name=body.name,
        due_date=body.due_date,
        priority=body.priority,
        position=_next_position(db, ProjectTask, project_id=project_id),
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.patch("/tasks/{task_id}")
async def update_task(task_id: int, body: TaskUpdateBody, db: Session = Depends(get_db_dependency)):
    task = db.get(ProjectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return _task_to_dict(task)


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: int, db: Session = Depends(get_db_dependency)):
    task = db.get(ProjectTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()


# ── dependencies ─────────────────────────────────────────────────────

@router.post("/tasks/{task_id}/dependencies", status_code=201)
async def add_dependency(task_id: int, body: DependencyCreate, db: Session = Depends(get_db_dependency)):
    if not db.get(ProjectTask, task_id) or not db.get(ProjectTask, body.depends_on_id):
        raise HTTPException(status_code=404, detail="Task not found")
    if task_id == body.depends_on_id:
        raise HTTPException(status_code=400, detail="A task cannot depend on itself")
    existing = db.get(TaskDependency, (task_id, body.depends_on_id))
    if not existing:
        db.add(TaskDependency(task_id=task_id, depends_on_id=body.depends_on_id))
        db.commit()
    return {"task_id": task_id, "depends_on_id": body.depends_on_id}


@router.delete("/tasks/{task_id}/dependencies/{depends_on_id}", status_code=204)
async def remove_dependency(task_id: int, depends_on_id: int, db: Session = Depends(get_db_dependency)):
    dep = db.get(TaskDependency, (task_id, depends_on_id))
    if dep:
        db.delete(dep)
        db.commit()


# ── status updates ───────────────────────────────────────────────────

@router.get("/{project_id}/updates")
async def list_updates(project_id: int, db: Session = Depends(get_db_dependency)):
    updates = db.query(ProjectUpdate).filter(
        ProjectUpdate.project_id == project_id
    ).order_by(ProjectUpdate.created_at.desc()).all()
    return [_update_to_dict(u) for u in updates]


@router.post("/{project_id}/updates", status_code=201)
async def create_update(project_id: int, body: StatusUpdateCreate, db: Session = Depends(get_db_dependency)):
    if not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    update = ProjectUpdate(
        project_id=project_id,
        status=body.status,
        body=body.body,
        created_at=datetime.utcnow().isoformat(),
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    return _update_to_dict(update)


@router.delete("/updates/{update_id}", status_code=204)
async def delete_update(update_id: int, db: Session = Depends(get_db_dependency)):
    update = db.get(ProjectUpdate, update_id)
    if not update:
        raise HTTPException(status_code=404, detail="Update not found")
    db.delete(update)
    db.commit()


# ── chat control-center ─────────────────────────────────────────────────

CHAT_SYSTEM_PROMPT = """You are Lattice — the single interface for this person's projects, tasks, \
and everything they capture. This chat is the only place they type things; whatever they say \
here, you route into the right place yourself. They never need a separate "brain dump" or "ask" \
screen — that's you too.

You help by walking through pending work, recording updates, creating projects and tasks via a \
brief interview, editing anything (rename tasks/projects, due dates, priority, effort, tags, \
milestone flag, move tasks between sections), creating sections, posting project status \
updates, capturing loose ideas/questions/references/reminders, answering questions from their \
vault, and deleting tasks/projects when the user clearly asks for it.

There are two separate task systems, listed separately in the context below:
- "Projects" — structured work with sections/milestones/dependencies (updates/new_tasks/etc below).
- "Quick tasks" — everything else: one-off errands, "remind me to...", class assignments, \
  follow-ups from a conversation. Default bucket is "daily" unless the user says otherwise \
  (weekly/long-term/someday). Use quick_tasks/quick_task_updates for these, NOT the project \
  fields — most casual updates from the user ("finished the reading", "need to email my advisor") \
  belong here, not in a Project.

If what they say isn't a task at all, file it instead of forcing it into one:
- "ideas" — a loose idea worth keeping, not actionable right now.
- "questions" — something they're wondering about / don't understand yet.
- "references" — a book/paper/video/article they want to read or watch later.
- "fleeting" — a short note or reminder too small to be a task.

If the user asks a question rather than giving an update, answer it using the "Vault \
knowledge" context block below if relevant (cite pages as [[concept]]) — put the answer in \
"reply" and leave updates/creates/deletes empty. If the vault context doesn't cover it, say so \
plainly instead of guessing.

Reply with ONLY a JSON object matching this exact schema (omit keys you have nothing for, use \
empty arrays/null where appropriate):

{
  "reply": "<string: what you say to the user>",
  "updates": [{"task_id": <id>, "name": "<opt>", "completed": <bool, opt>, "due_date": "<YYYY-MM-DD, opt>", "priority": "<Low|Medium|High|Urgent, opt>", "effort": <number, opt>, "tags": "<comma,separated, opt>", "is_milestone": <bool, opt>, "section": "<section name, opt>", "notes_append": "<text, opt>"}],
  "status_updates": [{"project_id": <id>, "status": "<on_track|at_risk|off_track|complete>", "body": "<text>"}],
  "new_project": {"name": "<name>", "description": "<10-20 words>", "sections": ["<opt>"], "tasks": [{"name": "<task>", "section": "<opt>", "due_date": "<opt>", "priority": "<opt>", "is_milestone": <opt bool>}]} or null,
  "new_tasks": [{"project_id": <id>, "name": "<task>", "due_date": "<opt>", "priority": "<opt>"}],
  "project_edits": [{"project_id": <id>, "name": "<opt>", "color": "<opt hex>", "description": "<opt>", "collaborators": "<opt comma,separated>"}],
  "new_sections": [{"project_id": <id>, "name": "<section name>"}],
  "delete_tasks": [<task_id>],
  "delete_projects": [<project_id>],
  "quick_tasks": [{"title": "<task>", "bucket": "<daily|weekly|long-term|someday, opt, default daily>", "priority": "<low|medium|high|urgent, opt>", "deadline": "<YYYY-MM-DD, opt>"}],
  "quick_task_updates": [{"task_id": "<id>", "completed": <bool, opt>, "title": "<opt>", "bucket": "<opt>", "priority": "<opt>", "deadline": "<opt>"}],
  "ideas": [{"text": "<idea>", "topic": "<opt>"}],
  "questions": [{"text": "<question>", "topic": "<opt>", "source": "<opt>"}],
  "references": [{"title": "<title>", "type": "<book|paper|video|article|other, opt>", "author": "<opt>", "action": "<read|watch|skim, opt>"}],
  "fleeting": [{"text": "<short note>"}]
}

Deletion is dangerous: only put an id in delete_tasks or delete_projects if the user's own \
message clearly names that exact item for deletion — the server double-checks this."""


def _build_chat_context(db: Session) -> str:
    projects = db.query(Project).order_by(Project.position).all()
    lines = []
    for p in projects:
        sections = db.query(ProjectSection).filter(ProjectSection.project_id == p.id).all()
        section_names = {s.id: s.name for s in sections}
        tasks = db.query(ProjectTask).filter(
            ProjectTask.project_id == p.id,
            ProjectTask.parent_id.is_(None),
            ProjectTask.completed.is_(False),
        ).all()
        latest = (
            db.query(ProjectUpdate)
            .filter(ProjectUpdate.project_id == p.id)
            .order_by(ProjectUpdate.created_at.desc())
            .first()
        )
        lines.append(f"Project id={p.id} name=\"{p.name}\" is_inbox={p.is_inbox} "
                      f"collaborators=\"{p.collaborators}\" sections={[s.name for s in sections]}")
        if p.description:
            lines.append(f"  description: {p.description}")
        for t in tasks:
            lines.append(
                f"  task_id={t.id} \"{t.name}\" section={section_names.get(t.section_id, '-')} "
                f"due_date={t.due_date} priority={t.priority} effort={t.effort} tags={t.tags} "
                f"is_milestone={t.is_milestone} notes={(t.notes or '')[:100]!r}"
            )
        if latest:
            lines.append(f"  latest_status: {latest.status} — {latest.body[:200]}")

    quick_tasks = db.query(Task).filter(Task.status != "done").order_by(Task.created_at.desc()).limit(50).all()
    lines.append("\nQuick tasks (not tied to a project):")
    if quick_tasks:
        for t in quick_tasks:
            lines.append(
                f"  task_id={t.id} \"{t.title}\" bucket={t.bucket} priority={t.priority} deadline={t.deadline}"
            )
    else:
        lines.append("  (none)")

    return "\n".join(lines) if lines else "(no projects yet)"


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]


def _resolve_section_id(db: Session, project_id: int, name: str) -> Optional[int]:
    section = db.query(ProjectSection).filter(
        ProjectSection.project_id == project_id, ProjectSection.name == name
    ).first()
    if section:
        return section.id
    section = ProjectSection(
        project_id=project_id, name=name,
        position=_next_position(db, ProjectSection, project_id=project_id),
    )
    db.add(section)
    db.flush()
    return section.id


@router.post("/chat")
async def chat(body: ChatRequest, db: Session = Depends(get_db_dependency)):
    if not body.messages:
        raise HTTPException(status_code=400, detail="messages required")

    last_user_msg = ""
    for m in reversed(body.messages):
        if m.role == "user":
            last_user_msg = m.content.lower()
            break

    context = _build_chat_context(db)
    transcript = "\n".join(f"{m.role}: {m.content}" for m in body.messages)

    vault_context = "(none)"
    if last_user_msg:
        from engines.rag_engine import get_rag_engine
        try:
            retrieved = await get_rag_engine().retrieve_context(last_user_msg, top_k=3)
            vault_context = retrieved["context"]
        except Exception as e:
            log.warning(f"Vault context retrieval failed, continuing without it: {e}")

    prompt = (
        f"Current state:\n{context}\n\n"
        f"Vault knowledge (may be relevant to the latest message):\n{vault_context}\n\n"
        f"Conversation:\n{transcript}"
    )

    try:
        result = await get_llm().complete_json(prompt, system=CHAT_SYSTEM_PROMPT)
    except Exception as e:
        log.error(f"Chat completion failed: {e}")
        raise HTTPException(status_code=502, detail=f"LLM error: {e}")

    now = datetime.utcnow().isoformat()

    for u in result.get("updates") or []:
        task_id = u.get("task_id")
        if not isinstance(task_id, int):
            continue
        task = db.get(ProjectTask, task_id)
        if not task:
            continue
        if "name" in u and u["name"]:
            task.name = u["name"]
        if "completed" in u and u["completed"] is not None:
            task.completed = u["completed"]
        if "due_date" in u and u["due_date"]:
            task.due_date = u["due_date"]
        if "priority" in u and u["priority"]:
            task.priority = u["priority"]
        if "effort" in u and u["effort"] is not None:
            task.effort = u["effort"]
        if "tags" in u and u["tags"] is not None:
            task.tags = u["tags"]
        if "is_milestone" in u and u["is_milestone"] is not None:
            task.is_milestone = u["is_milestone"]
        if u.get("section"):
            task.section_id = _resolve_section_id(db, task.project_id, u["section"])
        if u.get("notes_append"):
            task.notes = (task.notes or "") + ("\n" if task.notes else "") + u["notes_append"]

    for s in result.get("status_updates") or []:
        project_id = s.get("project_id")
        if not isinstance(project_id, int) or not db.get(Project, project_id):
            continue
        db.add(ProjectUpdate(
            project_id=project_id, status=s.get("status", "on_track"),
            body=s.get("body", ""), created_at=now,
        ))

    new_project_summary = None
    np = result.get("new_project")
    if np and np.get("name"):
        project = Project(
            name=np["name"],
            color=PROJECT_COLORS[db.query(Project).count() % len(PROJECT_COLORS)],
            position=_next_position(db, Project),
            description=np.get("description", ""),
            created_at=now,
        )
        db.add(project)
        db.flush()
        section_ids = {}
        for sname in np.get("sections") or []:
            sec = ProjectSection(
                project_id=project.id, name=sname,
                position=_next_position(db, ProjectSection, project_id=project.id),
            )
            db.add(sec)
            db.flush()
            section_ids[sname] = sec.id
        for t in np.get("tasks") or []:
            if not t.get("name"):
                continue
            section_id = section_ids.get(t.get("section")) if t.get("section") else None
            db.add(ProjectTask(
                project_id=project.id, section_id=section_id, name=t["name"],
                due_date=t.get("due_date"), priority=t.get("priority"),
                is_milestone=bool(t.get("is_milestone", False)),
                position=_next_position(db, ProjectTask, project_id=project.id),
                created_at=now,
            ))
        new_project_summary = {"id": project.id, "name": project.name}

    for nt in result.get("new_tasks") or []:
        project_id = nt.get("project_id")
        if not isinstance(project_id, int) or not db.get(Project, project_id) or not nt.get("name"):
            continue
        db.add(ProjectTask(
            project_id=project_id, name=nt["name"], due_date=nt.get("due_date"),
            priority=nt.get("priority"),
            position=_next_position(db, ProjectTask, project_id=project_id),
            created_at=now,
        ))

    for pe in result.get("project_edits") or []:
        project_id = pe.get("project_id")
        if not isinstance(project_id, int):
            continue
        project = db.get(Project, project_id)
        if not project:
            continue
        for field in ("name", "color", "description", "collaborators"):
            if pe.get(field):
                setattr(project, field, pe[field])

    for ns in result.get("new_sections") or []:
        project_id = ns.get("project_id")
        if not isinstance(project_id, int) or not db.get(Project, project_id) or not ns.get("name"):
            continue
        db.add(ProjectSection(
            project_id=project_id, name=ns["name"],
            position=_next_position(db, ProjectSection, project_id=project_id),
        ))

    # ── quick tasks — the plain daily/weekly/long-term/someday buckets,
    # separate from Project tasks above ──────────────────────────────────
    for qt in result.get("quick_tasks") or []:
        if not qt.get("title"):
            continue
        from engines.vault_writer import get_vault_writer
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id, title=qt["title"], bucket=qt.get("bucket") or "daily",
            priority=qt.get("priority") or "medium", status="inbox",
            deadline=qt.get("deadline"), source="chat", tags="[]",
            domain="academic", created_at=now, updated_at=now,
        )
        db.add(task)
        try:
            note_path = get_vault_writer().write_task_note({
                "id": task_id, "title": task.title, "bucket": task.bucket,
                "priority": task.priority, "status": task.status,
                "deadline": task.deadline, "source": "chat", "tags": [],
                "created_at": now,
            })
            task.vault_note_path = note_path
        except Exception as e:
            log.warning(f"Vault write failed for quick task: {e}")

    for qu in result.get("quick_task_updates") or []:
        task_id = qu.get("task_id")
        if not task_id:
            continue
        task = db.get(Task, task_id)
        if not task:
            continue
        if qu.get("title"):
            task.title = qu["title"]
        if qu.get("bucket"):
            task.bucket = qu["bucket"]
        if qu.get("priority"):
            task.priority = qu["priority"]
        if "deadline" in qu and qu["deadline"]:
            task.deadline = qu["deadline"]
        if qu.get("completed"):
            task.status = "done"
            task.completed_at = now
        task.updated_at = now

    # ── loose capture — ideas/questions/references/fleeting notes, the same
    # categories the old standalone Brain Dump page filed, now handled by this
    # one chat so there's a single place the user ever types anything ────────
    from engines.vault_writer import get_vault_writer as _get_vault_writer
    vault = _get_vault_writer()
    captured = {"ideas": [], "questions": [], "references": [], "fleeting": []}
    for item in result.get("ideas") or []:
        if not item.get("text"):
            continue
        try:
            vault.append_idea(item)
            captured["ideas"].append(item["text"])
        except Exception as e:
            log.warning(f"Idea write failed: {e}")
    for item in result.get("questions") or []:
        if not item.get("text"):
            continue
        try:
            vault.append_question(item)
            captured["questions"].append(item["text"])
        except Exception as e:
            log.warning(f"Question write failed: {e}")
    for item in result.get("references") or []:
        if not item.get("title"):
            continue
        try:
            vault.append_reading_list(item)
            captured["references"].append(item["title"])
        except Exception as e:
            log.warning(f"Reference write failed: {e}")
    for item in result.get("fleeting") or []:
        if not item.get("text"):
            continue
        try:
            vault.append_fleeting(item)
            captured["fleeting"].append(item["text"])
        except Exception as e:
            log.warning(f"Fleeting write failed: {e}")

    captured_count = sum(len(v) for v in captured.values())
    if captured_count:
        db.add(BrainDump(
            id=str(uuid.uuid4()), raw_text=last_user_msg, source="chat",
            processed_json=json.dumps(captured), items_extracted=captured_count,
            created_at=now,
        ))

    # ── deletions — require an explicit delete verb AND the item's exact
    # name as a whole word/phrase in the user's own message. A plain
    # substring check ("call" matching inside "recall", or matching any
    # message that happens to mention a short task name) let a hallucinated
    # delete_tasks/delete_projects entry from the model wipe real data with
    # no real confirmation.
    _DELETE_VERB = re.compile(r"\b(delete|remove|trash|get rid of|nuke)\b")
    has_delete_intent = bool(_DELETE_VERB.search(last_user_msg))

    def _name_in_message(name: str) -> bool:
        return bool(re.search(rf"\b{re.escape(name.lower())}\b", last_user_msg))

    for task_id in result.get("delete_tasks") or []:
        if not isinstance(task_id, int):
            continue
        task = db.get(ProjectTask, task_id)
        if not task or not has_delete_intent or not _name_in_message(task.name):
            continue
        db.delete(task)

    for project_id in result.get("delete_projects") or []:
        if not isinstance(project_id, int):
            continue
        project = db.get(Project, project_id)
        if not project or project.is_inbox:
            continue
        if not has_delete_intent or not _name_in_message(project.name) or not re.search(r"\bproject\b", last_user_msg):
            continue
        db.delete(project)

    db.commit()

    return {"reply": result.get("reply", ""), "new_project": new_project_summary}
