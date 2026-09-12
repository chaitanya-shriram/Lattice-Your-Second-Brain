import uuid
import json
import shutil
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

from config.prompts import FILE_METADATA_SYSTEM, FILE_METADATA_USER
from config.settings import get_settings
from storage.models import File as FileModel
from storage.database import get_db
from engines.vault_writer import get_vault_writer
from utils.file_utils import extract_text, is_supported
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("engines.file_ingest")

FOLDER_MAP = {
    "05-books/math": ["probability", "statistics", "measure-theory", "analysis", "linear-algebra"],
    "05-books/finance": ["finance", "trading", "derivatives", "economics", "quantitative-finance"],
    "05-books/cs": ["algorithms", "machine-learning", "software", "data-structures", "ml", "deep-learning"],
    "06-papers/probability": ["probability", "stochastic"],
    "06-papers/information-theory": ["information-theory", "entropy", "channel-capacity", "coding"],
    "06-papers/finance": ["finance", "derivatives", "portfolio", "risk"],
    "06-papers/machine-learning": ["machine-learning", "neural", "ml", "deep-learning"],
    "08-projects": ["assignment", "project", "code"],
}


def _infer_folder(metadata: dict) -> str:
    """Map topics to vault folder."""
    suggested = metadata.get("suggested_folder", "")
    if suggested and any(suggested.startswith(f) for f in FOLDER_MAP):
        return suggested

    topics = [t.lower() for t in metadata.get("primary_topics", [])]
    doc_type = metadata.get("document_type", "unknown").lower()

    is_book = "book" in doc_type or "textbook" in doc_type
    is_paper = "paper" in doc_type or "lecture" in doc_type or "notes" in doc_type

    for folder, keywords in FOLDER_MAP.items():
        if any(kw in topics for kw in keywords):
            if is_book and folder.startswith("05-"):
                return folder
            if is_paper and folder.startswith("06-"):
                return folder

    return "00-inbox"


class FileIngestEngine:
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm()
        self.vault = get_vault_writer()

    async def ingest(self, file_path: Path) -> dict:
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        if not is_supported(file_path):
            raise ValueError(f"Unsupported file type: {file_path.suffix}")

        log.info(f"Ingesting: {file_path.name}")

        # [1] Extract text
        text = extract_text(file_path)
        if not text.strip():
            text = f"[Could not extract text from {file_path.name}]"

        # [2] LLM metadata extraction
        prompt = FILE_METADATA_USER.format(first_pages_text=text[:4000])
        try:
            metadata = await self.llm.complete_json(prompt, system=FILE_METADATA_SYSTEM)
        except Exception as e:
            log.error(f"Metadata extraction failed: {e}")
            metadata = {
                "title": file_path.stem,
                "authors": [],
                "year": None,
                "document_type": "unknown",
                "primary_topics": [],
                "suggested_folder": "00-inbox",
                "canonical_filename": file_path.stem,
                "brief_description": "",
            }

        # [3] Determine canonical name
        canonical = metadata.get("canonical_filename", file_path.stem)
        canonical = _sanitize_filename(canonical)
        canonical_full = canonical + file_path.suffix

        # [4] Determine vault folder
        folder = _infer_folder(metadata)

        # [5] Move & rename file to vault-files/
        dest_dir = self.settings.vault_files_path / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / canonical_full

        if not dest.exists():
            shutil.copy2(str(file_path), str(dest))
            log.debug(f"Copied to: {dest}")

        # [6] Copy extracted text to raw folder
        raw_dir = self.settings.raw_path / "articles"
        raw_dir.mkdir(parents=True, exist_ok=True)
        raw_text_path = raw_dir / f"{canonical}.md"
        raw_text_path.write_text(
            f"---\nsource_file: {canonical_full}\ntitle: {metadata.get('title','')}\n---\n\n{text}",
            encoding="utf-8"
        )

        # [7] Create Obsidian note
        doc_type = metadata.get("document_type", "unknown")
        vault_folder = folder
        if "book" in doc_type or "textbook" in doc_type:
            note_path = self.vault.write_book_note(metadata, vault_folder)
        elif "paper" in doc_type or "lecture" in doc_type or "notes" in doc_type:
            note_path = self.vault.write_paper_note(metadata, vault_folder)
        else:
            note_path = self.vault.write_book_note(metadata, vault_folder)  # fallback

        # [8] Update bibliography
        try:
            self.vault.append_bibliography(metadata, note_path)
        except Exception as e:
            log.warning(f"Bibliography update failed: {e}")

        # [9] Store in SQLite
        file_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        with get_db() as db:
            file_record = FileModel(
                id=file_id,
                original_filename=file_path.name,
                canonical_filename=canonical_full,
                file_type=doc_type,
                topics=json.dumps(metadata.get("primary_topics", [])),
                authors=json.dumps(metadata.get("authors", [])),
                year=metadata.get("year"),
                stored_path=str(dest),
                vault_note_path=note_path,
                raw_path=str(raw_text_path),
                compiled=0,
                ingested_at=now,
            )
            db.add(file_record)

        # [10] Queue for wiki compilation (done separately by WikiCompiler)
        log.info(f"Ingested: {file_path.name} → {canonical_full} in {folder}")

        return {
            "file_id": file_id,
            "original_filename": file_path.name,
            "canonical_filename": canonical_full,
            "folder": folder,
            "vault_note_path": note_path,
            "raw_path": str(raw_text_path),
            "metadata": metadata,
            "compilation_queued": True,
        }

def _sanitize_filename(name: str) -> str:
    import re
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = name.replace(' ', '-')
    return name[:100]


_engine: FileIngestEngine | None = None


def get_file_ingest_engine() -> FileIngestEngine:
    global _engine
    if _engine is None:
        _engine = FileIngestEngine()
    return _engine
