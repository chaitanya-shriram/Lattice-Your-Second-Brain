from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter()


@router.get("/")
def get_graph():
    """Return full graph data (nodes + edges) for D3 visualization."""
    from engines.graph_builder import get_graph_builder
    builder = get_graph_builder()
    return builder.get_graph_data()


@router.post("/rebuild")
def rebuild_graph():
    """Trigger full graph rebuild from vault."""
    from engines.graph_builder import get_graph_builder
    builder = get_graph_builder()
    result = builder.build_all()
    return result


@router.get("/neighbors")
def get_neighbors(concept: str = Query(...), hops: int = Query(default=2, le=3)):
    """Get BFS neighborhood for a concept."""
    from engines.graph_builder import get_graph_builder
    builder = get_graph_builder()
    return builder.get_neighbors(concept, hops=hops)


class RAGQuery(BaseModel):
    question: str
    top_k: int = 5
    use_graph: bool = True


@router.post("/query")
async def rag_query(body: RAGQuery):
    """RAG query: embed → search → graph expand → synthesize."""
    from engines.rag_engine import get_rag_engine
    engine = get_rag_engine()
    result = await engine.query(
        body.question,
        top_k=body.top_k,
        use_graph=body.use_graph,
    )
    return result
