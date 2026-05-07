from __future__ import annotations

from src.models import QueryRequest, QueryResponse
from src.vector_store import query_chroma


def search_chunks(payload: QueryRequest) -> QueryResponse:
    results = query_chroma(
        strategy=payload.strategy,
        query=payload.query,
        top_k=payload.top_k,
        threshold=payload.threshold,
        doc_id=payload.doc_id,
    )
    return QueryResponse(
        strategy=payload.strategy,
        top_k=payload.top_k,
        threshold=payload.threshold,
        total_returned=len(results),
        results=results,
    )
