from __future__ import annotations

import shutil
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from src.config import settings
from src.ingest import extract_docx_to_sqlite, index_extracted_doc
from src.models import (
    ChunkStrategy,
    ExtractResponse,
    IndexRequest,
    IngestResponse,
    QueryRequest,
    QueryResponse,
)
from src.query import search_chunks
from src.storage_sqlite import SQLiteStore
from src.vector_store import clear_all_chroma_collections, list_chroma_collections, peek_chroma_collection


tags_metadata = [
    {"name": "system", "description": "API health and status checks"},
    {"name": "admin", "description": "Demo data administration operations"},
    {"name": "extract", "description": "Upload and extract .docx into SQLite"},
    {"name": "index", "description": "Chunk and embed data extracted from SQLite"},
    {"name": "query", "description": "Run topK/threshold vector search in Chroma"},
    {"name": "debug", "description": "Debug and inspect Chroma data"},
]

app = FastAPI(
    title="RAG Chunking Demo API",
    version="0.1.0",
    description=(
        "RAG demo that compares three chunking strategies: fixed, overlap, and semantic. "
        "Data is stored in SQLite (metadata/debug) and Chroma (vector search)."
    ),
    openapi_tags=tags_metadata,
    docs_url="/swagger",
    redoc_url="/redoc",
)
sqlite_store = SQLiteStore(settings.sqlite_path)


@app.get("/health", tags=["system"], summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.delete(
    "/admin/clear-data",
    tags=["admin"],
    summary="Delete all SQLite and Chroma data",
)
def clear_all_data():
    try:
        sqlite_deleted = sqlite_store.clear_all_extracted_blocks()
        chroma_result = clear_all_chroma_collections()
        return {
            "message": "All demo data cleared",
            "sqlite_deleted_rows": sqlite_deleted,
            "chroma_deleted_collections": chroma_result.get("deleted_collections", []),
            "chroma_deleted_count": chroma_result.get("deleted_count", 0),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Clear data failed: {exc}") from exc


@app.post(
    "/extract",
    tags=["extract"],
    response_model=ExtractResponse,
    summary="Upload docx and extract blocks into SQLite",
    description=(
        "Accept a .docx file, parse it into metadata blocks (heading/paragraph/list/table), "
        "and save them into the extracted_blocks table in SQLite."
    ),
)
async def extract_file(
    file: UploadFile = File(..., description=".docx file to ingest"),
):
    if not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx is supported")

    upload_dir = Path("data/uploads")
    upload_dir.mkdir(parents=True, exist_ok=True)
    target_path = upload_dir / file.filename

    with target_path.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        result = extract_docx_to_sqlite(
            file_path=str(target_path),
            sqlite_store=sqlite_store,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Extract failed: {exc}") from exc


@app.post(
    "/index",
    tags=["index"],
    response_model=IngestResponse,
    summary="Choose strategy to chunk and embed into Chroma",
    description=(
        "Use extracted data from SQLite (by doc_id), chunk it by strategy, "
        "create embeddings, and upsert into the corresponding Chroma collection.\n\n"
        "Required payload by strategy:\n"
        "- fixed: doc_id, strategy='fixed', chunk_size\n"
        "- overlap: doc_id, strategy='overlap', chunk_size, overlap (must be < chunk_size)\n"
        "- semantic: doc_id, strategy='semantic' (chunk_size/overlap are optional and ignored)"
    ),
)
def index_document(payload: IndexRequest):
    try:
        chunk_size = payload.chunk_size if payload.chunk_size is not None else 500
        overlap = payload.overlap if payload.overlap is not None else 0
        return index_extracted_doc(
            doc_id=payload.doc_id,
            strategy=payload.strategy,
            chunk_size=chunk_size,
            overlap=overlap,
            sqlite_store=sqlite_store,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Index failed: {exc}") from exc


@app.post(
    "/query",
    tags=["query"],
    response_model=QueryResponse,
    summary="Query topK chunks from Chroma",
    description=(
        "Accept query text, create query embedding, find topK chunks in the target strategy "
        "collection, and optionally filter by similarity threshold."
    ),
)
def query(payload: QueryRequest):
    try:
        return search_chunks(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query failed: {exc}") from exc


@app.get(
    "/debug/chroma/collections",
    tags=["debug"],
    summary="List Chroma collections",
)
def debug_chroma_collections():
    try:
        return {"collections": list_chroma_collections()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Debug failed: {exc}") from exc


@app.get(
    "/debug/chroma/peek",
    tags=["debug"],
    summary="Peek documents in strategy collection",
)
def debug_chroma_peek(
    strategy: ChunkStrategy,
    limit: int = 5,
    include_embeddings: bool = False,
):
    try:
        if limit < 1 or limit > 500:
            raise HTTPException(status_code=400, detail="limit must be between 1 and 500")
        return peek_chroma_collection(
            strategy=strategy,
            limit=limit,
            include_embeddings=include_embeddings,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Debug failed: {exc}") from exc
