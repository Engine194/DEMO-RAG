from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.document import Document as _Document
from docx.table import Table
from docx.text.paragraph import Paragraph

from src.models import ChunkBlock


def iter_block_items(parent: _Document):
    body = parent.element.body
    for child in body.iterchildren():
        if child.tag.endswith("}p"):
            yield Paragraph(child, parent)
        elif child.tag.endswith("}tbl"):
            yield Table(child, parent)


def normalize_text(value: str) -> str:
    return " ".join(value.replace("\n", " ").split())


def flatten_table(table: Table) -> str:
    rows = []
    for row in table.rows:
        cells = [normalize_text(cell.text) for cell in row.cells]
        rows.append(" | ".join(cells))
    return "\n".join(rows)


def load_docx_blocks(file_path: str) -> list[ChunkBlock]:
    path = Path(file_path)
    doc = Document(path)
    blocks: list[ChunkBlock] = []
    heading_path: list[str] = []

    for idx, block in enumerate(iter_block_items(doc)):
        if isinstance(block, Paragraph):
            text = normalize_text(block.text)
            if not text:
                continue

            style_name = block.style.name if block.style is not None else ""
            block_type = "paragraph"
            heading_level = None

            if style_name.startswith("Heading"):
                block_type = "heading"
                digits = "".join(ch for ch in style_name if ch.isdigit())
                heading_level = int(digits) if digits else 1
                heading_path = heading_path[: heading_level - 1] + [text]
            elif style_name.startswith("List"):
                block_type = "list_item"

            blocks.append(
                ChunkBlock(
                    text=text,
                    block_type=block_type,
                    heading_path=list(heading_path),
                    heading_level=heading_level,
                    block_index=idx,
                )
            )
        else:
            table_text = flatten_table(block)
            if not table_text.strip():
                continue
            blocks.append(
                ChunkBlock(
                    text=table_text,
                    block_type="table",
                    heading_path=list(heading_path),
                    heading_level=None,
                    block_index=idx,
                )
            )

    return blocks
