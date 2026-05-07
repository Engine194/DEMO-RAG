from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    azure_openai_endpoint: str = os.getenv("OPENAI_ENDPOINT", "")
    azure_openai_key: str = os.getenv("OPENAI_KEY", "")
    azure_openai_embedding_deployment: str = os.getenv("OPENAI_EMBEDDING_DEPLOYMENT", "")
    azure_openai_api_version: str = os.getenv("OPENAI_API_VERSION", "2024-02-01")
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma")
    sqlite_path: str = os.getenv("SQLITE_PATH", "./data/rag_demo.db")
    collection_prefix: str = os.getenv("COLLECTION_PREFIX", "word_docs")
    embedding_batch_size: int = int(os.getenv("EMBEDDING_BATCH_SIZE", "20"))
    embedding_max_retries: int = int(os.getenv("EMBEDDING_MAX_RETRIES", "5"))
    embedding_retry_base_seconds: float = float(os.getenv("EMBEDDING_RETRY_BASE_SECONDS", "2"))


settings = Settings()
