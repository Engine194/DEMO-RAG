from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


ChunkStrategy = Literal["fixed", "overlap", "semantic"]


class ChunkBlock(BaseModel):
    text: str
    block_type: str
    heading_path: list[str] = Field(default_factory=list)
    heading_level: int | None = None
    block_index: int


class ChunkRecord(BaseModel):
    chunk_id: str
    strategy: ChunkStrategy
    doc_id: str
    source_file: str
    chunk_text: str
    heading_path: list[str] = Field(default_factory=list)
    block_type: str = "paragraph"
    heading_level: int | None = None
    block_index: int = -1
    chunk_index: int
    token_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExtractResponse(BaseModel):
    doc_id: str = Field(description="Extracted document ID")
    source_file: str = Field(description="Source docx filename")
    total_blocks: int = Field(description="Total blocks saved to SQLite")


class IngestResponse(BaseModel):
    doc_id: str = Field(description="Document ID used for indexing")
    strategy: ChunkStrategy = Field(description="Chunking strategy used")
    total_blocks: int = Field(description="Total parsed blocks from docx")
    total_chunks: int = Field(description="Total chunks after splitting")
    collection: str = Field(description="Target Chroma collection name")


class IndexRequest(BaseModel):
    doc_id: str = Field(description="Document ID that was extracted earlier")
    strategy: ChunkStrategy = Field(
        description=(
            "Chunking strategy to index. "
            "fixed requires chunk_size; overlap requires chunk_size + overlap; "
            "semantic only requires doc_id + strategy."
        )
    )
    chunk_size: int | None = Field(
        default=None,
        ge=1,
        description=(
            "Chunk length for fixed/overlap (required). "
            "Optional and ignored for semantic."
        ),
    )
    overlap: int | None = Field(
        default=None,
        ge=0,
        description=(
            "Overlap length for overlap strategy (required, must be < chunk_size). "
            "Optional and ignored for fixed/semantic."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "doc_id": "ab12cd34ef56",
                    "strategy": "fixed",
                    "chunk_size": 500,
                },
                {
                    "doc_id": "ab12cd34ef56",
                    "strategy": "overlap",
                    "chunk_size": 500,
                    "overlap": 100,
                },
                {
                    "doc_id": "ab12cd34ef56",
                    "strategy": "semantic",
                },
            ]
        }
    }

    @model_validator(mode="after")
    def validate_by_strategy(self) -> "IndexRequest":
        if self.strategy in {"fixed", "overlap"} and self.chunk_size is None:
            raise ValueError("chunk_size is required for fixed and overlap strategies")
        if self.strategy == "overlap":
            if self.overlap is None:
                raise ValueError("overlap is required for overlap strategy")
            if self.chunk_size is not None and self.overlap >= self.chunk_size:
                raise ValueError("overlap must be less than chunk_size")
        return self


class QueryRequest(BaseModel):
    query: str = Field(description="Question or search text")
    strategy: ChunkStrategy = Field(description="Chunking strategy to query")
    top_k: int = Field(default=5, ge=1, le=20, description="Maximum number of results")
    threshold: float | None = Field(
        default=None,
        ge=0,
        le=1,
        description="Minimum similarity threshold (0-1). No filter when null.",
    )
    doc_id: str | None = Field(default=None, description="Optional doc_id filter")

    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "Dieu kien thanh toan gom nhung gi?",
                "strategy": "semantic",
                "top_k": 5,
                "threshold": 0.75,
                "doc_id": None,
            }
        }
    }


class QueryResultItem(BaseModel):
    rank: int = Field(description="Result ranking position")
    chunk_id: str = Field(description="Chunk identifier")
    distance: float = Field(description="Vector distance (lower is better)")
    similarity: float = Field(description="Converted similarity (higher is better)")
    text: str = Field(description="Chunk text content")
    metadata: dict[str, Any] = Field(description="Chunk metadata")


class QueryResponse(BaseModel):
    strategy: ChunkStrategy = Field(description="Queried chunking strategy")
    top_k: int = Field(description="Requested top K")
    threshold: float | None = Field(default=None, description="Applied similarity threshold")
    total_returned: int = Field(description="Number of results after filtering")
    results: list[QueryResultItem] = Field(description="Retrieved chunk list")
