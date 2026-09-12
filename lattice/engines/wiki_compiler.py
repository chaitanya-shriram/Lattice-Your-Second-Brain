import uuid
import json
from pathlib import Path
from datetime import datetime

from config.prompts import WIKI_COMPILER_SYSTEM, WIKI_COMPILER_USER
from config.settings import get_settings
from storage.models import WikiPage, File as FileModel
from storage.database import get_db
from engines.vault_writer import get_vault_writer
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("engines.wiki_compiler")


class WikiCompiler:
    """
    Karpathy-pattern compiler: reads raw sources → compiles into interconnected wiki pages.
    Always single-source incremental (never batch) for best synthesis quality.
    """

    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm()
        self.vault_writer = get_vault_writer()

    async def compile_source(self, source_path: Path) -> dict:
        """Compile a single raw source file into wiki pages."""
        if not source_path.exists():
            raise FileNotFoundError(f"Source not found: {source_path}")

        source_text = source_path.read_text(encoding="utf-8", errors="replace")
        source_title = source_path.stem

        log.info(f"Compiling wiki from: {source_path.name}")

        # Load existing wiki context (semantic search if embeddings exist, else load index)
        existing_wiki_context = await self._load_relevant_wiki(source_text[:2000])

        prompt = WIKI_COMPILER_USER.format(
            existing_wiki_context=existing_wiki_context,
            source_title=source_title,
            source_text=source_text[:6000],
        )

        try:
            result = await self.llm.complete_json(prompt, system=WIKI_COMPILER_SYSTEM)
        except Exception as e:
            log.error(f"Wiki compilation LLM call failed: {e}")
            return {"error": str(e), "source": source_path.name}

        now = datetime.utcnow().isoformat()
        pages_created = []
        pages_updated = []
        contradictions = []

        # Write new pages
        for page in result.get("pages_to_create", []):
            try:
                vault_path = self.vault_writer.write_wiki_page(page)

                with get_db() as db:
                    wiki_page = WikiPage(
                        id=str(uuid.uuid4()),
                        concept=page.get("title", page.get("filename", "Unknown")),
                        folder=page.get("folder", "general"),
                        vault_path=vault_path,
                        domain=page.get("domain", "academic"),
                        source_files=json.dumps([str(source_path)]),
                        confidence=page.get("confidence", "medium"),
                        has_contradictions=0,
                        version=1,
                        created_at=now,
                        last_compiled=now,
                    )
                    db.add(wiki_page)

                pages_created.append(vault_path)
                log.debug(f"Created wiki page: {vault_path}")
            except Exception as e:
                log.error(f"Failed to create wiki page '{page.get('title')}': {e}")

        # Update existing pages
        for update in result.get("pages_to_update", []):
            try:
                vault_path = update.get("path", "")
                page_contradictions = update.get("contradictions", [])
                updated_path = self.vault_writer.update_wiki_page(
                    vault_path,
                    update.get("additions", ""),
                    page_contradictions or None,
                )
                pages_updated.append(updated_path)
                if page_contradictions:
                    contradictions.extend(page_contradictions)

                with get_db() as db:
                    wiki_record = db.query(WikiPage).filter(
                        WikiPage.vault_path == vault_path
                    ).first()
                    if wiki_record:
                        wiki_record.version += 1
                        wiki_record.last_compiled = now
                        if page_contradictions:
                            wiki_record.has_contradictions = 1

            except Exception as e:
                log.error(f"Failed to update wiki page '{update.get('path')}': {e}")

        # Append to memory log
        log_entry = result.get("log_entry", f"Compiled {source_path.name}")
        await self._append_memory(log_entry)

        # Mark source file as compiled in DB (if it's a tracked file)
        await self._mark_compiled(source_path, [*pages_created, *pages_updated])

        total = len(pages_created) + len(pages_updated)
        log.info(f"Wiki compiled: {len(pages_created)} created, {len(pages_updated)} updated from {source_path.name}")

        return {
            "source": source_path.name,
            "pages_created": pages_created,
            "pages_updated": pages_updated,
            "contradictions": contradictions,
            "total_pages_affected": total,
            "log_entry": log_entry,
        }

    async def compile_all_uncompiled(self) -> list[dict]:
        """Process all raw files that haven't been compiled yet."""
        raw_path = self.settings.raw_path
        results = []

        for f in raw_path.rglob("*.md"):
            if "processed" in str(f):
                continue
            result = await self.compile_source(f)
            results.append(result)

            # Move to processed after successful compilation
            processed = raw_path / "processed"
            processed.mkdir(exist_ok=True)
            try:
                f.rename(processed / f.name)
            except Exception:
                pass  # already processed or conflict

        return results

    async def _load_relevant_wiki(self, query_text: str) -> str:
        """Load relevant wiki pages for context. Falls back to index if no embeddings."""
        wiki_path = self.settings.wiki_path
        if not wiki_path.exists():
            return "No existing wiki pages yet."

        wiki_files = list(wiki_path.rglob("*.md"))
        if not wiki_files:
            return "No existing wiki pages yet."

        # Simple heuristic: load _index.md + up to 3 random pages
        # (full semantic search enabled once embeddings engine is wired in Phase 5)
        context_parts = []

        index = wiki_path / "_index.md"
        if index.exists():
            context_parts.append("=== Wiki Index ===\n" + index.read_text(encoding="utf-8")[:500])

        import random
        sample = random.sample(wiki_files, min(3, len(wiki_files)))
        for f in sample:
            if f.name != "_index.md":
                content = f.read_text(encoding="utf-8")[:800]
                context_parts.append(f"=== {f.stem} ===\n{content}")

        return "\n\n".join(context_parts) or "No existing wiki context."

    async def _append_memory(self, log_entry: str):
        """Append to _context/memory.md."""
        memory_path = self.settings.context_path / "memory.md"
        memory_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H:%M")
        entry = f"\n## {timestamp}\n- {log_entry}\n"

        if memory_path.exists():
            content = memory_path.read_text(encoding="utf-8")
        else:
            content = "# Lattice Memory Log\n"

        memory_path.write_text(content + entry, encoding="utf-8")

    async def _mark_compiled(self, source_path: Path, wiki_paths: list[str]):
        """Mark file record as compiled in SQLite."""
        source_str = str(source_path)
        now = datetime.utcnow().isoformat()
        with get_db() as db:
            file_record = db.query(FileModel).filter(
                FileModel.raw_path == source_str
            ).first()
            if file_record:
                file_record.compiled = 1
                file_record.compiled_at = now
                file_record.wiki_pages = json.dumps(wiki_paths)


_compiler: WikiCompiler | None = None


def get_wiki_compiler() -> WikiCompiler:
    global _compiler
    if _compiler is None:
        _compiler = WikiCompiler()
    return _compiler
