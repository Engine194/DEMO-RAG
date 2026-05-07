from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from src.models import ChunkBlock


class SQLiteStore:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _ensure_tables(self) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS extracted_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT NOT NULL,
                source_file TEXT NOT NULL,
                block_index INTEGER NOT NULL,
                block_text TEXT NOT NULL,
                block_type TEXT,
                heading_path TEXT,
                heading_level INTEGER
            )
            """
        )
        conn.commit()
        conn.close()

    def save_extracted_blocks(self, *, doc_id: str, source_file: str, blocks: list[ChunkBlock]) -> None:
        conn = self._connect()
        cur = conn.cursor()
        cur.execute("DELETE FROM extracted_blocks WHERE doc_id = ?", (doc_id,))
        cur.executemany(
            """
            INSERT INTO extracted_blocks (
                doc_id, source_file, block_index, block_text, block_type, heading_path, heading_level
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    doc_id,
                    source_file,
                    block.block_index,
                    block.text,
                    block.block_type,
                    json.dumps(block.heading_path, ensure_ascii=False),
                    block.heading_level,
                )
                for block in blocks
            ],
        )
        conn.commit()
        conn.close()

    def get_extracted_blocks(self, doc_id: str) -> tuple[str, list[ChunkBlock]]:
        conn = self._connect()
        cur = conn.cursor()
        rows = cur.execute(
            """
            SELECT source_file, block_index, block_text, block_type, heading_path, heading_level
            FROM extracted_blocks
            WHERE doc_id = ?
            ORDER BY block_index ASC
            """,
            (doc_id,),
        ).fetchall()
        conn.close()

        if not rows:
            return "", []

        source_file = str(rows[0][0])
        blocks = [
            ChunkBlock(
                block_index=int(row[1]),
                text=str(row[2]),
                block_type=str(row[3]),
                heading_path=json.loads(row[4]) if row[4] else [],
                heading_level=int(row[5]) if row[5] is not None else None,
            )
            for row in rows
        ]
        return source_file, blocks

    def clear_all_extracted_blocks(self) -> int:
        conn = self._connect()
        cur = conn.cursor()
        count_row = cur.execute("SELECT COUNT(*) FROM extracted_blocks").fetchone()
        deleted = int(count_row[0]) if count_row else 0
        cur.execute("DELETE FROM extracted_blocks")
        conn.commit()
        conn.close()
        return deleted
