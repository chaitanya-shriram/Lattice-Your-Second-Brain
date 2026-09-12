import asyncio
import socket
from fastapi import APIRouter
from fastapi.responses import Response
from datetime import datetime

from config.settings import get_settings

router = APIRouter()

LATTICE_VERSION = "2.0.0"


def _local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        try:
            s.close()
        except Exception:
            pass


@router.get("/")
async def health_check():
    settings = get_settings()

    def _check_ollama():
        try:
            import ollama
            ollama.list()
            return True
        except Exception:
            return False

    ollama_ok, db_ok = False, False

    ollama_ok = await asyncio.to_thread(_check_ollama)

    if settings.is_configured:
        try:
            from storage.database import get_db
            from storage.models import Project
            with get_db() as db:
                db.query(Project).first()
                db_ok = True
        except Exception:
            pass

    local_ip = _local_ip()
    port = settings.api_port

    return {
        "status": "ok" if db_ok else ("setup_required" if not settings.is_configured else "degraded"),
        "configured": settings.is_configured,
        "timestamp": datetime.utcnow().isoformat(),
        "version": LATTICE_VERSION,
        "ollama": "ok" if ollama_ok else "unavailable",
        "db": "ok" if db_ok else ("n/a" if not settings.is_configured else "error"),
        "llm_backend": settings.llm_backend,
        "model": settings.ollama_primary_model,
        "lan_url": f"http://{local_ip}:{port}",
        "vault_path": str(settings.vault_path) if settings.vault_path else None,
        "vault_files_path": str(settings.vault_files_path) if settings.vault_files_path else None,
        "incoming_path": str(settings.incoming_path) if settings.incoming_path else None,
        "db_path": str(settings.db_path) if settings.db_path else None,
        "logs_path": str(settings.logs_path) if settings.logs_path else None,
    }


@router.get("/qr")
async def lan_qr():
    """Return a QR code PNG for the LAN URL — scan from phone to open Lattice."""
    settings = get_settings()
    local_ip = _local_ip()
    url = f"http://{local_ip}:{settings.api_port}"

    def _make():
        try:
            import qrcode
            import io
            qr = qrcode.QRCode(box_size=6, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="#5C7CFA", back_color="#0F1117")
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf.getvalue()
        except ImportError:
            return None

    png = await asyncio.to_thread(_make)
    if png is None:
        return Response(status_code=503, content="qrcode package not installed")
    return Response(content=png, media_type="image/png")
