from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


@router.post("/run")
def run_health_check():
    from engines.self_improve import get_self_improve_engine
    engine = get_self_improve_engine()
    return engine.run_full_check()


@router.get("/reports")
def get_reports(limit: int = Query(default=10, le=50)):
    from engines.self_improve import get_self_improve_engine
    engine = get_self_improve_engine()
    return engine.get_recent_reports(limit)


# Journal routes
journal_router = APIRouter()


class JournalEntryRequest(BaseModel):
    text: str
    reflect: bool = True


@journal_router.post("/")
async def add_journal_entry(body: JournalEntryRequest):
    from engines.journal_engine import get_journal_engine
    engine = get_journal_engine()
    return await engine.add_entry(body.text, prompt_reflection=body.reflect)


@journal_router.get("/today")
async def today_summary():
    from engines.journal_engine import get_journal_engine
    engine = get_journal_engine()
    return await engine.get_today_summary()


@journal_router.get("/entries")
def get_entries(limit: int = Query(default=10, le=50)):
    from engines.journal_engine import get_journal_engine
    engine = get_journal_engine()
    return engine.get_entries(limit)


# CRM routes
crm_router = APIRouter()


class ContactRequest(BaseModel):
    name: str
    role: str | None = None
    institution: str | None = None
    email: str | None = None
    context: str | None = None
    tags: list[str] = []


@crm_router.post("/")
def upsert_contact(body: ContactRequest):
    from engines.crm_engine import get_crm_engine
    engine = get_crm_engine()
    return engine.upsert_contact(
        name=body.name,
        role=body.role,
        institution=body.institution,
        email=body.email,
        context=body.context,
        tags=body.tags,
    )


@crm_router.get("/")
def list_contacts(search: str | None = None):
    from engines.crm_engine import get_crm_engine
    engine = get_crm_engine()
    return engine.list_contacts(search)


@crm_router.get("/{contact_id}")
def get_contact(contact_id: str):
    from engines.crm_engine import get_crm_engine
    engine = get_crm_engine()
    contact = engine.get_contact(contact_id)
    if not contact:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Contact not found")
    return contact
