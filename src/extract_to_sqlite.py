from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from src.docx_loader import load_docx_blocks
from src.storage_sqlite import SQLiteStore


def extract_only(file_path: str, sqlite_path: str) -> dict[str, int | str]:
    blocks = load_docx_blocks(file_path)
    doc_id = uuid4().hex[:12]
    source_file = Path(file_path).name

    store = SQLiteStore(sqlite_path)
    store.save_extracted_blocks(doc_id=doc_id, source_file=source_file, blocks=blocks)
    return {"doc_id": doc_id, "total_blocks": len(blocks), "sqlite_path": sqlite_path}
