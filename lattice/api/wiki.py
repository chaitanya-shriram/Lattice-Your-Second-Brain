from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import WikiPage

router = APIRouter()


@router.get("/")
def list_wiki(
    folder: str | None = None,
    domain: str | None = None,
    db: Session = Depends(get_db_dependency),
):
    q = db.query(WikiPage)
    if folder:
        q = q.filter(WikiPage.folder == folder)
    if domain:
        q = q.filter(WikiPage.domain == domain)
    pages = q.order_by(WikiPage.last_compiled.desc()).all()
    return [
        {
            "id": p.id,
            "concept": p.concept,
            "folder": p.folder,
            "domain": p.domain,
            "vault_path": p.vault_path,
            "confidence": p.confidence,
            "version": p.version,
            "has_contradictions": bool(p.has_contradictions),
            "last_compiled": p.last_compiled,
            "created_at": p.created_at,
        }
        for p in pages
    ]


@router.get("/search")
def search_wiki(q: str = Query(..., min_length=1), db: Session = Depends(get_db_dependency)):
    pages = (
        db.query(WikiPage)
        .filter(WikiPage.concept.ilike(f"%{q}%"))
        .limit(20)
        .all()
    )
    return [
        {
            "id": p.id,
            "concept": p.concept,
            "folder": p.folder,
            "vault_path": p.vault_path,
        }
        for p in pages
    ]


@router.get("/{page_id}")
def get_wiki_page(page_id: str, db: Session = Depends(get_db_dependency)):
    page = db.query(WikiPage).filter(WikiPage.id == page_id).first()
    if not page:
        raise HTTPException(status_code=404, detail="Wiki page not found")

    content = None
    try:
        from pathlib import Path
        p = Path(page.vault_path)
        if p.exists():
            content = p.read_text(encoding="utf-8")
    except Exception:
        pass

    return {
        "id": page.id,
        "concept": page.concept,
        "folder": page.folder,
        "domain": page.domain,
        "vault_path": page.vault_path,
        "confidence": page.confidence,
        "version": page.version,
        "has_contradictions": bool(page.has_contradictions),
        "source_files": page.source_files,
        "last_compiled": page.last_compiled,
        "created_at": page.created_at,
        "content": content,
    }
