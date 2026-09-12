import asyncio
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config.settings import get_settings
from utils.logger import get_logger
from utils.file_utils import is_supported

log = get_logger("engines.vault_watcher")


class IncomingHandler(FileSystemEventHandler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop

    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if is_supported(path):
            log.info(f"New file detected: {path.name}")
            asyncio.run_coroutine_threadsafe(self._process(path), self.loop)

    async def _process(self, path: Path):
        try:
            from engines.file_ingest import get_file_ingest_engine
            engine = get_file_ingest_engine()
            result = await engine.ingest(path)
            log.info(f"Auto-ingested: {path.name} → {result.get('canonical_filename')}")

            # Queue wiki compilation
            if result.get("raw_path") and get_settings().wiki_compilation_enabled:
                from engines.wiki_compiler import get_wiki_compiler
                compiler = get_wiki_compiler()
                await compiler.compile_source(Path(result["raw_path"]))
        except Exception as e:
            log.error(f"Auto-ingest failed for {path.name}: {e}")


class VaultWatcher:
    def __init__(self, incoming_path: Path, vault_path: Path, loop: asyncio.AbstractEventLoop):
        self.incoming_path = incoming_path
        self.vault_path = vault_path
        self.loop = loop
        self._observer: Observer | None = None

    def start(self):
        self.incoming_path.mkdir(parents=True, exist_ok=True)
        handler = IncomingHandler(self.loop)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.incoming_path), recursive=False)
        self._observer.start()
        log.info(f"Watching incoming folder: {self.incoming_path}")

    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
            log.info("Vault watcher stopped")
