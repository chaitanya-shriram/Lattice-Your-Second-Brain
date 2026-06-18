import shutil
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import File as FileModel
from config.settings import get_settings

router = APIRouter()


@router.get("/")
async def list_files(db: Session = Depends(get_db_dependency)):
    import json
    files = db.query(FileModel).order_by(FileModel.ingested_at.desc()).all()
    return [
        {
            "id": f.id,
            "original_filename": f.original_filename,
            "canonical_filename": f.canonical_filename,
            "file_type": f.file_type,
            "topics": json.loads(f.topics) if f.topics else [],
            "authors": json.loads(f.authors) if f.authors else [],
            "year": f.year,
            "stored_path": f.stored_path,
            "vault_note_path": f.vault_note_path,
            "compiled": bool(f.compiled),
            "ingested_at": f.ingested_at,
        }
        for f in files
    ]


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Receive file, save to incoming/, queue for ingestion (Phase 3)."""
    settings = get_settings()
    dest = settings.incoming_path / file.filename
    dest.parent.mkdir(parents=True, exist_ok=True)

    with open(dest, "wb") as f:
        content = await file.read()
        f.write(content)

    return {
        "status": "received",
        "filename": file.filename,
        "size_bytes": len(content),
        "message": "File saved to incoming/. Ingestion pipeline active in Phase 3.",
        "path": str(dest),
    }
