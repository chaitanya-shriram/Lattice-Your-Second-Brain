import sys
import os
import mimetypes

# Fix Windows registry MIME type bugs for static file serving
mimetypes.add_type("application/javascript", ".js")
mimetypes.add_type("text/css", ".css")

# Add lattice/ to path so imports work when run from lattice/ dir
sys.path.insert(0, os.path.dirname(__file__))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pathlib import Path

from config.settings import get_settings
from storage.database import init_db
from utils.logger import setup_logger, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    setup_logger()
    log = get_logger("main")
    log.info("Lattice starting up...")

    if not settings.is_configured:
        log.warning("Paths not configured — open http://localhost:8080 to complete setup")
        yield
        log.info("Lattice shutting down")
        return

    settings.ensure_dirs()
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
        loop = asyncio.get_running_loop()
        watcher = VaultWatcher(settings.incoming_path, settings.vault_path, loop)
        watcher.start()
        app.state.watcher = watcher
    except Exception as e:
        log.warning(f"Vault watcher failed to start: {e}")

    # Telegram bot: text-in from your phone (no exposed port, see engines/telegram_bot.py)
    try:
        if settings.telegram_bot_token:
            import asyncio
            from engines.telegram_bot import poll_forever
            asyncio.ensure_future(poll_forever())
        else:
            log.info("Telegram bot disabled (set TELEGRAM_BOT_TOKEN to enable)")
    except Exception as e:
        log.warning(f"Telegram bot failed to start: {e}")

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

@app.exception_handler(Exception)
async def exception_handler(request: Request, exc: Exception):
    get_logger("main").error(f"Unhandled error on {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"error": "Internal server error"})


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # LAN access; no external exposure
    allow_credentials=False,  # auth is a Bearer header, not cookies — no credentials needed
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Optional API key auth. Set LATTICE_API_KEY in .env to enable."""
    settings = get_settings()
    key = settings.lattice_api_key
    if not key:
        return await call_next(request)

    path = request.url.path
    # Exempt: static frontend files
    if not path.startswith("/api/"):
        return await call_next(request)
    # Setup routes are only exempt before first-run configuration is done —
    # once configured, /api/setup/save and /restart must respect the key too.
    if path.startswith("/api/setup/") and not settings.is_configured:
        return await call_next(request)

    auth = request.headers.get("Authorization", "")
    if auth == f"Bearer {key}":
        return await call_next(request)

    return JSONResponse({"detail": "Unauthorized"}, status_code=401)

# ── API routes ─────────────────────────────────────────────────────────
from api.setup import router as setup_router
from api.tasks import router as tasks_router
from api.dump import router as dump_router
from api.files import router as files_router
from api.health import router as health_router
from api.wiki import router as wiki_router
from api.graph import router as graph_router
from api.skills import router as skills_router
from api.health_checks import router as health_checks_router, journal_router, crm_router
from api.backup import router as backup_router
from api.projects import router as projects_router
from api.intents import router as intents_router
from api.daily_review import router as daily_review_router

app.include_router(setup_router, prefix="/api/setup", tags=["setup"])
app.include_router(tasks_router, prefix="/api/tasks", tags=["tasks"])
app.include_router(dump_router, prefix="/api/dump", tags=["dump"])
app.include_router(files_router, prefix="/api/files", tags=["files"])
app.include_router(health_router, prefix="/api/health", tags=["health"])
app.include_router(wiki_router, prefix="/api/wiki", tags=["wiki"])
app.include_router(graph_router, prefix="/api/graph", tags=["graph"])
app.include_router(skills_router, prefix="/api/skills", tags=["skills"])
app.include_router(health_checks_router, prefix="/api/vault-health", tags=["vault-health"])
app.include_router(journal_router, prefix="/api/journal", tags=["journal"])
app.include_router(crm_router, prefix="/api/crm", tags=["crm"])
app.include_router(backup_router, prefix="/api/backup", tags=["backup"])
app.include_router(projects_router, prefix="/api/projects", tags=["projects"])
app.include_router(intents_router, prefix="/api/intents", tags=["intents"])
app.include_router(daily_review_router, prefix="/api/daily-review", tags=["daily-review"])

# ── Frontend static files ───────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    _frontend_dist = Path(sys.executable).parent / "frontend" / "dist"
else:
    _frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    dist = _frontend_dist
    # Serve the exact file if it exists (JS, CSS, SVG, etc.)
    if full_path:
        static_file = dist / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(str(static_file))
    # SPA fallback
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
