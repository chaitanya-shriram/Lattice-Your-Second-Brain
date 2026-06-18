"""
Embeddings indexer: scans vault wiki pages + raw files → embeds → stores.
Called on startup to pre-index existing content, and after each compilation.
Only indexes content not yet embedded (checks by source_type+source_id).
"""
import hashlib
from pathlib import Path
from datetime import datetime

from storage.database import get_db
from storage.models import Embedding, WikiPage
from llm.embeddings import embed_and_store
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("engines.embeddings_indexer")


class EmbeddingsIndexer:
    def __init__(self):
        from config.settings import get_settings
        self.settings = get_settings()
        self.llm = get_llm()

    def _already_indexed(self, source_type: str, source_id: str) -> bool:
        with get_db() as db:
            exists = (
                db.query(Embedding)
                .filter(
                    Embedding.source_type == source_type,
                    Embedding.source_id == source_id,
                )
                .first()
            )
            return exists is not None

    async def index_wiki_pages(self) -> dict:
        """Embed all wiki pages not yet in embeddings table."""
        with get_db() as db:
            pages = db.query(WikiPage).all()
            page_data = [
                {"id": p.id, "concept": p.concept, "vault_path": p.vault_path}
                for p in pages
            ]

        indexed = 0
        skipped = 0

        for pd in page_data:
            source_id = f"wiki:{pd['id']}"
            if self._already_indexed("wiki", source_id):
                skipped += 1
                continue

            try:
                path = self.settings.vault_path / pd["vault_path"]
                if not path.exists():
                    continue
                content = path.read_text(encoding="utf-8", errors="replace")
                if not content.strip():
                    continue

                text = f"# {pd['concept']}\n\n{content[:4000]}"
                with get_db() as db:
                    await embed_and_store(text, "wiki", source_id, db)

                indexed += 1
                log.debug(f"Indexed wiki: {pd['concept']}")
            except Exception as e:
                log.warning(f"Failed to index wiki {pd['concept']}: {e}")

        log.info(f"Wiki indexing: {indexed} new, {skipped} already indexed")
        return {"wiki_indexed": indexed, "wiki_skipped": skipped}

    async def index_raw_files(self) -> dict:
        """Embed raw text files in vault/00-raw/."""
        raw_path = self.settings.raw_path
        if not raw_path.exists():
            return {"raw_indexed": 0, "raw_skipped": 0}

        indexed = 0
        skipped = 0

        for md_file in raw_path.rglob("*.md"):
            source_id = f"raw:{md_file.stem}"
            if self._already_indexed("raw", source_id):
                skipped += 1
                continue

            try:
                content = md_file.read_text(encoding="utf-8", errors="replace")
                if not content.strip():
                    continue

                with get_db() as db:
                    await embed_and_store(content[:6000], "raw", source_id, db)

                indexed += 1
                log.debug(f"Indexed raw: {md_file.name}")
            except Exception as e:
                log.warning(f"Failed to index raw {md_file.name}: {e}")

        log.info(f"Raw file indexing: {indexed} new, {skipped} already indexed")
        return {"raw_indexed": indexed, "raw_skipped": skipped}

    async def run_full_index(self) -> dict:
        """Index all wiki pages + raw files."""
        log.info("Running full embeddings index")
        r1 = await self.index_wiki_pages()
        r2 = await self.index_raw_files()
        return {**r1, **r2}

    def get_stats(self) -> dict:
        with get_db() as db:
            total = db.query(Embedding).count()
            wiki_count = (
                db.query(Embedding)
                .filter(Embedding.source_type == "wiki")
                .count()
            )
            raw_count = (
                db.query(Embedding)
                .filter(Embedding.source_type == "raw")
                .count()
            )
        return {
            "total_embeddings": total,
            "wiki_chunks": wiki_count,
            "raw_chunks": raw_count,
        }


_indexer: EmbeddingsIndexer | None = None


def get_embeddings_indexer() -> EmbeddingsIndexer:
    global _indexer
    if _indexer is None:
        _indexer = EmbeddingsIndexer()
    return _indexer
