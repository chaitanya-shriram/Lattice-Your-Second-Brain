import sys
import os

# Add lattice/ to path so imports work when run from lattice/ dir
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from config.settings import get_settings
from storage.database import init_db
from utils.logger import setup_logger, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    settings.ensure_dirs()
    setup_logger()
    log = get_logger("main")
    log.info("Lattice starting up...")
    init_db()
    log.info(f"DB initialized at {settings.db_path}")
    log.info(f"Vault at {settings.vault_path}")
    log.info(f"LLM backend: {settings.llm_backend} ({settings.ollama_primary_model})")
    log.info(f"Server: http://{settings.api_host}:{settings.api_port}")

    # Load skills on startup
    try:
        from engines.skill_engine import get_skill_engine
        get_skill_engine().load_skills()
    except Exception as e:
        log.warning(f"Skill loading failed: {e}")

    # Start scheduler
    try:
        from engines.scheduler import get_scheduler
        get_scheduler().start()
    except Exception as e:
        log.warning(f"Scheduler failed to start: {e}")

    # Start vault watcher
    try:
        import asyncio
        from engines.vault_watcher import VaultWatcher
        loop = asyncio.get_event_loop()
        watcher = VaultWatcher(settings.incoming_path, settings.vault_path, loop)
        watcher.start()
        app.state.watcher = watcher
    except Exception as e:
        log.warning(f"Vault watcher failed to start: {e}")

    # Pre-index embeddings in background (non-blocking)
    try:
        import asyncio
        from engines.embeddings_indexer import get_embeddings_indexer

        async def _run_index():
            try:
                result = await get_embeddings_indexer().run_full_index()
                log.info(f"Embeddings indexed: {result}")
            except Exception as exc:
                log.warning(f"Embeddings indexing failed: {exc}")

        asyncio.ensure_future(_run_index())
        log.info("Embeddings indexer scheduled as background task")
    except Exception as e:
        log.warning(f"Embeddings indexer setup failed: {e}")

    yield

    # Shutdown
    try:
        from engines.scheduler import get_scheduler
        get_scheduler().stop()
    except Exception:
        pass
    try:
        if hasattr(app.state, "watcher"):
            app.state.watcher.stop()
    except Exception:
        pass
    log.info("Lattice shutting down")


app = FastAPI(
    title="Lattice",
    description="Local AI Knowledge OS — your second brain, fully offline",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN access; no external exposure
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ─────────────────────────────────────────────────────────
from api.tasks import router as tasks_router
from api.dump import router as dump_router
from api.files import router as files_router
from api.health import router as health_router
from api.wiki import router as wiki_router
from api.actions import router as actions_router
from api.graph import router as graph_router
from api.skills import router as skills_router
from api.health_checks import router as health_checks_router, journal_router, crm_router
from api.gamification_api import router as gamification_router

app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(dump_router, prefix="/api/dump", tags=["dump"])
app.include_router(files_router, prefix="/api/files", tags=["files"])
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(wiki_router, prefix="/api/wiki", tags=["wiki"])
app.include_router(actions_router, prefix="/api/actions", tags=["actions"])
app.include_router(graph_router, prefix="/api/graph", tags=["graph"])
app.include_router(skills_router, prefix="/api/skills", tags=["skills"])
app.include_router(health_checks_router, prefix="/api/vault-health", tags=["vault-health"])
app.include_router(journal_router, prefix="/api/journal", tags=["journal"])
app.include_router(crm_router, prefix="/api/crm", tags=["crm"])
app.include_router(gamification_router, prefix="/api/xp", tags=["gamification"])

# ── Frontend static files ───────────────────────────────────────────────
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if _frontend_dist.exists():
    _assets = _frontend_dist / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
    index = dist / "index.html"
    if index.exists():
        return FileResponse(str(index))
    return {
        "message": "Lattice API running",
        "version": "2.0.0",
        "docs": "/docs",
        "note": "Frontend not built yet. Run: cd frontend && npm run build",
    }


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="warning",
    )
