import json
import uuid
import numpy as np
from datetime import datetime
from sqlalchemy.orm import Session
from storage.models import Embedding
from storage.database import get_db
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("llm.embeddings")

CHUNK_SIZE = 512  # tokens approximated by chars/4


def _chunk_text(text: str, chunk_size: int = CHUNK_SIZE) -> list[str]:
    words = text.split()
    chunks, current = [], []
    current_len = 0
    for word in words:
        word_len = len(word) // 4 + 1
        if current_len + word_len > chunk_size and current:
            chunks.append(" ".join(current))
            current, current_len = [], 0
        current.append(word)
        current_len += word_len
    if current:
        chunks.append(" ".join(current))
    return chunks or [text]


async def embed_and_store(
    text: str,
    source_type: str,
    source_id: str,
    db: Session | None = None,
) -> list[str]:
    llm = get_llm()
    chunks = _chunk_text(text)
    ids = []

    def _store(session: Session):
        session.query(Embedding).filter(
            Embedding.source_type == source_type,
            Embedding.source_id == source_id,
        ).delete()

        for i, chunk in enumerate(chunks):
            vec = None
            try:
                import asyncio
                vec = asyncio.get_event_loop().run_until_complete(llm.embed(chunk))
            except Exception as e:
                log.warning(f"Embed chunk {i} failed: {e}")
                continue

            emb = Embedding(
                id=str(uuid.uuid4()),
                source_type=source_type,
                source_id=source_id,
                chunk_index=i,
                text_chunk=chunk,
                embedding=json.dumps(vec),
                created_at=datetime.utcnow().isoformat(),
            )
            session.add(emb)
            ids.append(emb.id)

    if db is not None:
        _store(db)
    else:
        with get_db() as session:
            _store(session)

    log.debug(f"Embedded {source_type}/{source_id}: {len(chunks)} chunks")
    return ids


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.array(a), np.array(b)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def search_embeddings(
    query_vec: list[float],
    db: Session,
    top_k: int = 5,
    source_type: str | None = None,
    min_similarity: float = 0.0,
) -> list[dict]:
    q = db.query(Embedding)
    if source_type:
        q = q.filter(Embedding.source_type == source_type)
    rows = q.all()

    scored = []
    for row in rows:
        try:
            vec = json.loads(row.embedding)
            sim = cosine_similarity(query_vec, vec)
            if sim >= min_similarity:
                scored.append({
                    "source_type": row.source_type,
                    "source_id": row.source_id,
                    "chunk_index": row.chunk_index,
                    "text_chunk": row.text_chunk,
                    "similarity": sim,
                })
        except Exception:
            continue

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]
