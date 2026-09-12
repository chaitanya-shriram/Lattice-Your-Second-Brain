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
    """Embed text chunks and store in DB. Fully async — no event loop gymnastics."""
    llm = get_llm()
    chunks = _chunk_text(text)

    # Embed all chunks asynchronously first
    embedded: list[tuple[int, str, list[float]]] = []
    for i, chunk in enumerate(chunks):
        try:
            vec = await llm.embed(chunk)
            embedded.append((i, chunk, vec))
        except Exception as e:
            log.warning(f"Embed chunk {i} failed for {source_type}/{source_id}: {e}")

    if not embedded:
        log.warning(f"All chunks failed to embed for {source_type}/{source_id}")
        return []

    # Write to DB in a single transaction
    ids: list[str] = []
    now = datetime.utcnow().isoformat()

    def _store(session: Session):
        session.query(Embedding).filter(
            Embedding.source_type == source_type,
            Embedding.source_id == source_id,
        ).delete()

        for idx, chunk, vec in embedded:
            emb = Embedding(
                id=str(uuid.uuid4()),
                source_type=source_type,
                source_id=source_id,
                chunk_index=idx,
                text_chunk=chunk,
                embedding=json.dumps(vec),
                created_at=now,
            )
            session.add(emb)
            ids.append(emb.id)

    if db is not None:
        _store(db)
    else:
        with get_db() as session:
            _store(session)

    log.debug(f"Embedded {source_type}/{source_id}: {len(embedded)}/{len(chunks)} chunks stored")
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
    # ponytail: still an O(n) full-table scan (every embedding loaded into
    # memory each query) — fine for a personal vault's chunk count, but the
    # ceiling is a real vector index (sqlite-vec, faiss) once this is
    # thousands+ of chunks. The numpy batch matmul below is just a constant-
    # factor speedup over the old per-row Python loop, not a Big-O fix.
    q = db.query(Embedding)
    if source_type:
        q = q.filter(Embedding.source_type == source_type)
    rows = q.all()
    if not rows:
        return []

    vecs, valid_rows = [], []
    for row in rows:
        try:
            vecs.append(json.loads(row.embedding))
            valid_rows.append(row)
        except Exception:
            continue
    if not vecs:
        return []

    query = np.array(query_vec)
    mat = np.array(vecs)
    query_norm = np.linalg.norm(query)
    row_norms = np.linalg.norm(mat, axis=1)
    denom = row_norms * query_norm
    sims = np.divide(mat @ query, denom, out=np.zeros(len(mat)), where=denom != 0)

    order = np.argsort(-sims)
    scored = []
    for i in order:
        sim = float(sims[i])
        if sim < min_similarity:
            break
        row = valid_rows[i]
        scored.append({
            "source_type": row.source_type,
            "source_id": row.source_id,
            "chunk_index": row.chunk_index,
            "text_chunk": row.text_chunk,
            "similarity": sim,
        })
        if len(scored) >= top_k:
            break

    return scored
