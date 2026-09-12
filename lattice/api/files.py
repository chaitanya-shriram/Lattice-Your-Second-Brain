import shutil
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from sqlalchemy.orm import Session

from storage.database import get_db_dependency
from storage.models import File as FileModel
from config.settings import get_settings
from utils.file_utils import SUPPORTED_EXTENSIONS

router = APIRouter()

MAX_UPLOAD_BYTES = 500 * 1024 * 1024  # 500 MB


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
async def upload_file(request: Request, file: UploadFile = File(...)):
    """Receive file, save to incoming/, queue for ingestion (Phase 3)."""
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(status_code=503, detail="Lattice not configured — complete setup first")

    # Strip directory components to prevent path traversal
    safe_name = Path(file.filename).name
    if not safe_name:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if Path(safe_name).suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    # Reject oversized uploads from the Content-Length header before buffering
    # the body — a client-supplied header isn't proof of actual size, so the
    # chunked read below still enforces the real cap either way.
    declared_size = request.headers.get("content-length")
    if declared_size and int(declared_size) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Max {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
        )

    dest = settings.incoming_path / safe_name
    dest.parent.mkdir(parents=True, exist_ok=True)

    size = 0
    tmp = dest.with_name(dest.name + ".part")
    with open(tmp, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                f.close()
                tmp.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Max {MAX_UPLOAD_BYTES // (1024*1024)} MB.",
                )
            f.write(chunk)
    tmp.replace(dest)

    return {
        "status": "received",
        "filename": safe_name,
        "size_bytes": size,
        "message": "File saved to incoming/. Ingestion pipeline active in Phase 3.",
        "path": str(dest),
    }
