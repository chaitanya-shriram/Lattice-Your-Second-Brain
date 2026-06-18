from fastapi import APIRouter
from datetime import datetime
import subprocess

from config.settings import get_settings
from storage.database import get_db
from storage.models import GamificationStats

router = APIRouter()


@router.get("/")
async def health_check():
    settings = get_settings()
    ollama_ok = False
    try:
        import ollama
        ollama.list()
        ollama_ok = True
    except Exception:
        pass

    db_ok = False
    try:
        with get_db() as db:
            db.query(GamificationStats).first()
            db_ok = True
    except Exception:
        pass

    return {
        "status": "ok" if (db_ok) else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "ollama": "ok" if ollama_ok else "unavailable",
        "db": "ok" if db_ok else "error",
        "llm_backend": settings.llm_backend,
        "model": settings.ollama_primary_model,
        "vault_path": str(settings.vault_path),
    }
