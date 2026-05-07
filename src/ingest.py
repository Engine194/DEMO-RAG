from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.chunking import build_chunks
from src.docx_loader import load_docx_blocks
from src.models import ChunkStrategy, ExtractResponse, IngestResponse
from src.storage_sqlite import SQLiteStore
from src.vector_store import upsert_chunks_to_chroma


def extract_docx_to_sqlite(
    *,
    file_path: str,
    sqlite_store: SQLiteStore,
) -> ExtractResponse:
    blocks = load_docx_blocks(file_path)
    doc_id = uuid4().hex[:12]
    source_file = Path(file_path).name
    sqlite_store.save_extracted_blocks(doc_id=doc_id, source_file=source_file, blocks=blocks)

    return ExtractResponse(
        doc_id=doc_id,
        source_file=source_file,
        total_blocks=len(blocks),
    )


def index_extracted_doc(
    *,
    doc_id: str,
    strategy: ChunkStrategy,
    sqlite_store: SQLiteStore,
    chunk_size: int = 500,
    overlap: int = 100,
) -> IngestResponse:
    source_file, blocks = sqlite_store.get_extracted_blocks(doc_id)
    if not blocks:
        raise ValueError(f"No extracted blocks found for doc_id={doc_id}")

    chunks = build_chunks(
        blocks=blocks,
        strategy=strategy,
        doc_id=doc_id,
        source_file=source_file,
        chunk_size=chunk_size,
        overlap=overlap,
    )
    collection = upsert_chunks_to_chroma(strategy, chunks)

    return IngestResponse(
        doc_id=doc_id,
        strategy=strategy,
        total_blocks=len(blocks),
        total_chunks=len(chunks),
        collection=collection,
    )
