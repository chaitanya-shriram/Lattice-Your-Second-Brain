"""
Phase 5 tests: Graph Builder + RAG Engine.
"""
import pytest
import sys
import os
import asyncio
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_graph_builder_vault_links():
    from engines.graph_builder import GraphBuilder
    builder = GraphBuilder()
    result = builder.build_vault_links()
    assert "links_created" in result
    assert isinstance(result["links_created"], int)
    print(f"  Vault links: {result['links_created']}")


def test_graph_builder_concept_edges():
    from engines.graph_builder import GraphBuilder
    builder = GraphBuilder()
    result = builder.build_wiki_concept_edges()
    assert "edges_created" in result
    assert isinstance(result["edges_created"], int)
    print(f"  Concept edges: {result['edges_created']}")


def test_graph_builder_all():
    from engines.graph_builder import GraphBuilder
    builder = GraphBuilder()
    result = builder.build_all()
    assert "links_created" in result
    assert "edges_created" in result
    assert "graph_edges" in result
    print(f"  Full graph: {result}")


def test_graph_get_data():
    from engines.graph_builder import GraphBuilder
    builder = GraphBuilder()
    data = builder.get_graph_data()
    assert "nodes" in data
    assert "edges" in data
    assert isinstance(data["nodes"], list)
    assert isinstance(data["edges"], list)
    # Should have 2 wiki pages from Phase 3
    print(f"  Graph nodes: {len(data['nodes'])}, edges: {len(data['edges'])}")


def test_graph_neighbors():
    from engines.graph_builder import GraphBuilder
    builder = GraphBuilder()
    result = builder.get_neighbors("Entropy", hops=2)
    assert "center" in result
    assert "neighbors" in result
    assert isinstance(result["neighbors"], list)
    print(f"  Entropy neighbors: {result['neighbors']}")


def test_search_embeddings_ranks_and_filters():
    """Vectorized search_embeddings: top-k ordering, min_similarity cutoff, source_type filter."""
    import json
    import uuid
    from datetime import datetime
    from llm.embeddings import search_embeddings
    from storage.database import get_db
    from storage.models import Embedding

    now = datetime.utcnow().isoformat()
    rows = [
        ("close", [1.0, 0.0, 0.0], "wiki"),
        ("far", [0.0, 1.0, 0.0], "wiki"),
        ("opposite", [-1.0, 0.0, 0.0], "wiki"),
        ("other_type", [1.0, 0.0, 0.0], "task"),
    ]
    ids = []
    with get_db() as db:
        for source_id, vec, source_type in rows:
            e = Embedding(
                id=str(uuid.uuid4()), source_type=source_type, source_id=f"test-{source_id}",
                chunk_index=0, text_chunk=source_id, embedding=json.dumps(vec), created_at=now,
            )
            db.add(e)
            ids.append(e.id)

    try:
        with get_db() as db:
            results = search_embeddings([1.0, 0.0, 0.0], db, top_k=2, source_type="wiki")
        assert [r["source_id"] for r in results] == ["test-close", "test-far"]  # ranked, opposite excluded by top_k
        assert results[0]["similarity"] > results[1]["similarity"]

        with get_db() as db:
            results = search_embeddings([1.0, 0.0, 0.0], db, top_k=10, source_type="wiki", min_similarity=0.5)
        assert [r["source_id"] for r in results] == ["test-close"]  # far (sim=0) and opposite (sim=-1) filtered out
    finally:
        with get_db() as db:
            db.query(Embedding).filter(Embedding.id.in_(ids)).delete(synchronize_session=False)


def test_rag_engine_imports():
    from engines.rag_engine import RAGEngine
    engine = RAGEngine()
    assert engine is not None


def test_rag_query_mock():
    """RAG query with mock LLM (no Ollama needed)."""
    import asyncio
    from engines.rag_engine import RAGEngine

    class MockLLM:
        async def embed(self, text):
            return [0.1] * 768
        async def complete(self, prompt, system="", schema=None, model=None):
            return "This is a synthesized answer about entropy from the vault context."
        async def complete_json(self, prompt, system="", model=None, retries=2):
            return {}

    engine = RAGEngine()
    engine.llm = MockLLM()

    result = asyncio.run(engine.query("What is entropy?", top_k=3))
    assert "question" in result
    assert "answer" in result
    assert "sources_used" in result
    assert result["question"] == "What is entropy?"
    assert len(result["answer"]) > 0
    print(f"  RAG answer: {result['answer'][:80]}...")


def test_graph_api_import():
    from api.graph import router
    assert router is not None


def test_graph_rebuild_endpoint():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.post("/api/graph/rebuild")
    assert r.status_code == 200
    data = r.json()
    assert "links_created" in data


def test_graph_data_endpoint():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)
    r = client.get("/api/graph/")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "edges" in data


def test_rag_query_endpoint():
    from fastapi.testclient import TestClient
    from main import app
    from engines.rag_engine import get_rag_engine

    class MockLLM:
        async def embed(self, text):
            return [0.1] * 768
        async def complete(self, prompt, system="", schema=None, model=None):
            return "Answer synthesized from vault."
        async def complete_json(self, prompt, system="", model=None, retries=2):
            return {}

    engine = get_rag_engine()
    engine.llm = MockLLM()

    client = TestClient(app)
    r = client.post("/api/graph/query", json={"question": "What is entropy?", "top_k": 3})
    assert r.status_code == 200
    data = r.json()
    assert "answer" in data
    assert "wiki_pages_used" in data
    print(f"  API RAG answer: {data['answer'][:60]}...")
