from __future__ import annotations

import math
from uuid import uuid4

from src.models import ChunkBlock, ChunkRecord, ChunkStrategy


def estimate_token_count(text: str) -> int:
    return max(1, math.ceil(len(text) / 4))


def chunk_text_fixed(text: str, chunk_size: int, overlap: int = 0) -> list[str]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be > 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be >= 0 and < chunk_size")

    chunks: list[str] = []
    start = 0
    step = chunk_size - overlap
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks


def build_chunks(
    *,
    blocks: list[ChunkBlock],
    strategy: ChunkStrategy,
    doc_id: str,
    source_file: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[ChunkRecord]:
    records: list[ChunkRecord] = []
    chunk_index = 0

    for block in blocks:
        if strategy == "semantic":
            pieces = [block.text]
        elif strategy == "fixed":
            pieces = chunk_text_fixed(block.text, chunk_size=chunk_size, overlap=0)
        else:
            pieces = chunk_text_fixed(block.text, chunk_size=chunk_size, overlap=overlap)

        for piece in pieces:
            metadata = {
                "doc_id": doc_id,
                "source_file": source_file,
                "strategy": strategy,
                "heading_path": " > ".join(block.heading_path),
                "block_type": block.block_type,
                "chunk_index": chunk_index,
                "block_index": block.block_index,
            }

            records.append(
                ChunkRecord(
                    chunk_id=f"{strategy}_{uuid4().hex[:12]}_{chunk_index}",
                    strategy=strategy,
                    doc_id=doc_id,
                    source_file=source_file,
                    chunk_text=piece,
                    heading_path=block.heading_path,
                    block_type=block.block_type,
                    heading_level=block.heading_level,
                    block_index=block.block_index,
                    chunk_index=chunk_index,
                    token_count=estimate_token_count(piece),
                    metadata=metadata,
                )
            )
            chunk_index += 1

    return records
