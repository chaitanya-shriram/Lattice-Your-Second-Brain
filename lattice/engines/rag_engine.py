"""
RAG Engine: query → embed → search → graph expand → synthesize answer.
"""
from pathlib import Path
from datetime import datetime

from config.settings import get_settings
from config.prompts import RAG_SYNTHESIS_SYSTEM, RAG_SYNTHESIS_USER
from storage.database import get_db
from storage.models import WikiPage, Task, BrainDump
from llm.embeddings import search_embeddings
from llm.router import get_llm
from utils.logger import get_logger

log = get_logger("engines.rag_engine")


class RAGEngine:
    def __init__(self):
        self.settings = get_settings()
        self.llm = get_llm()

    async def query(self, question: str, top_k: int = 5, use_graph: bool = True) -> dict:
        """
        Full RAG pipeline:
        1. Embed question
        2. Search embedding store for top-k chunks
        3. Optionally BFS-expand via graph
        4. Load wiki context for matched concepts
        5. LLM synthesis
        """
        log.info(f"RAG query: {question[:80]}")

        # [1] Embed query
        try:
            query_vec = await self.llm.embed(question)
        except Exception as e:
            log.warning(f"Embedding failed, falling back to keyword search: {e}")
            query_vec = None

        # [2] Search embeddings + wiki
        embedding_chunks = []
        wiki_contexts = []

        if query_vec:
            with get_db() as db:
                hits = search_embeddings(query_vec, db, top_k=top_k)
                embedding_chunks = hits

        # [3] Load wiki pages relevant to question (keyword fallback)
        wiki_contexts = await self._load_wiki_context(question, top_k=3)

        # [4] Graph expansion
        graph_contexts = []
        if use_graph and wiki_contexts:
            graph_contexts = await self._expand_via_graph(wiki_contexts, hops=1)

        # [5] Build context block
        context_parts = []

        for chunk in embedding_chunks[:top_k]:
            context_parts.append(
                f"[Source: {chunk.get('source_type','?')} | {chunk.get('source_id','?')}]\n"
                f"{chunk.get('chunk_text', '')}"
            )

        for wiki in wiki_contexts:
            context_parts.append(
                f"[Wiki: {wiki['concept']} ({wiki['folder']})]\n{wiki['content'][:600]}"
            )

        for gc in graph_contexts[:2]:
            context_parts.append(
                f"[Related: {gc['concept']}]\n{gc['content'][:400]}"
            )

        context = "\n\n---\n\n".join(context_parts) or "No relevant context found in vault."

        # [6] LLM synthesis
        try:
            prompt = RAG_SYNTHESIS_USER.format(
                question=question,
                context=context,
            )
            answer = await self.llm.complete(prompt, system=RAG_SYNTHESIS_SYSTEM)
        except Exception as e:
            log.error(f"RAG synthesis failed: {e}")
            answer = f"Error: {e}"

        return {
            "question": question,
            "answer": answer,
            "sources_used": len(embedding_chunks) + len(wiki_contexts),
            "wiki_pages_used": [w["concept"] for w in wiki_contexts],
            "graph_expanded": len(graph_contexts),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def _load_wiki_context(self, question: str, top_k: int = 3) -> list[dict]:
        """Keyword search over wiki concepts + load content."""
        keywords = question.lower().split()

        with get_db() as db:
            pages = db.query(WikiPage).all()
            page_dicts = [
                {
                    "concept": p.concept,
                    "folder": p.folder,
                    "vault_path": p.vault_path,
                }
                for p in pages
            ]

        results = []
        for pd in page_dicts:
            score = sum(1 for kw in keywords if kw in pd["concept"].lower())
            if score > 0:
                content = _load_page_content(pd["vault_path"], self.settings.vault_path)
                results.append({**pd, "content": content, "score": score})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    async def _expand_via_graph(self, wiki_contexts: list[dict], hops: int = 1) -> list[dict]:
        """Expand context via graph neighbors."""
        from engines.graph_builder import get_graph_builder
        builder = get_graph_builder()
        expanded = []
        seen = {w["concept"] for w in wiki_contexts}

        for wiki in wiki_contexts[:2]:
            result = builder.get_neighbors(wiki["concept"], hops=hops)
            for neighbor_concept in result.get("neighbors", [])[:2]:
                if neighbor_concept not in seen:
                    seen.add(neighbor_concept)
                    with get_db() as db:
                        page = (
                            db.query(WikiPage)
                            .filter(WikiPage.concept.ilike(f"%{neighbor_concept}%"))
                            .first()
                        )
                        if page:
                            pd = {
                                "concept": page.concept,
                                "folder": page.folder,
                                "vault_path": page.vault_path,
                            }
                    if page:
                        content = _load_page_content(pd["vault_path"], self.settings.vault_path)
                        expanded.append({**pd, "content": content})

        return expanded


def _load_page_content(vault_path: str, vault: Path) -> str:
    """Load wiki page content from disk."""
    try:
        path = vault / vault_path
        if path.exists():
            return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        pass
    return ""


_engine: RAGEngine | None = None


def get_rag_engine() -> RAGEngine:
    global _engine
    if _engine is None:
        _engine = RAGEngine()
    return _engine
