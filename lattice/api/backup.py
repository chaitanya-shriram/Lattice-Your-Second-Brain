import asyncio
import io
import zipfile
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from config.settings import get_settings

router = APIRouter()


@router.post("/create")
async def create_backup():
    """
    Stream a ZIP containing the full vault + SQLite DB.
    Safe to call while server is running — reads DB file directly (SQLite WAL is read-safe).
    """
    settings = get_settings()
    if not settings.is_configured:
        raise HTTPException(503, "Lattice not configured yet")

    def _build_zip() -> tuple[io.BytesIO, str]:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        buf = io.BytesIO()

        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
            # Vault (all markdown + assets)
            vault: Path = settings.vault_path
            if vault and vault.exists():
                for f in vault.rglob("*"):
                    if f.is_file():
                        zf.write(f, Path("vault") / f.relative_to(vault))

            # Vault files (PDFs, images, etc.)
            vfiles: Path = settings.vault_files_path
            if vfiles and vfiles.exists():
                for f in vfiles.rglob("*"):
                    if f.is_file():
                        zf.write(f, Path("vault-files") / f.relative_to(vfiles))

            # SQLite DB
            db: Path = settings.db_path
            if db and db.exists():
                zf.write(db, f"lattice_{stamp}.db")

        buf.seek(0)
        return buf, stamp

    buf, stamp = await asyncio.to_thread(_build_zip)
    filename = f"lattice_backup_{stamp}.zip"

    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
