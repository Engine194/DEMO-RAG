from __future__ import annotations

import time
from pathlib import Path

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_openai import AzureOpenAIEmbeddings, OpenAIEmbeddings

from src.config import settings
from src.models import ChunkRecord, QueryResultItem


def _to_json_list(value):
    if value is None:
        return []
    if hasattr(value, "tolist"):
        value = value.tolist()
    return list(value)


def get_embeddings() -> OpenAIEmbeddings | AzureOpenAIEmbeddings:
    if (
        settings.azure_openai_endpoint
        and settings.azure_openai_key
        and settings.azure_openai_embedding_deployment
    ):
        return AzureOpenAIEmbeddings(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_key,
            azure_deployment=settings.azure_openai_embedding_deployment,
            openai_api_version=settings.azure_openai_api_version,
        )

    if not settings.openai_api_key:
        raise ValueError(
            "Missing embedding credentials. Set OPENAI_API_KEY (OpenAI) "
            "or OPENAI_ENDPOINT + OPENAI_KEY + OPENAI_EMBEDDING_DEPLOYMENT (Azure OpenAI)."
        )
    return OpenAIEmbeddings(
        api_key=settings.openai_api_key,
        model=settings.embedding_model,
    )


def get_collection_name(strategy: str) -> str:
    return f"{settings.collection_prefix}_{strategy}"


def get_vector_store(strategy: str) -> Chroma:
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=get_collection_name(strategy),
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_persist_dir,
    )


def upsert_chunks_to_chroma(strategy: str, chunks: list[ChunkRecord]) -> str:
    store = get_vector_store(strategy)
    batch_size = max(1, settings.embedding_batch_size)
    max_retries = max(0, settings.embedding_max_retries)
    base_delay = max(0.5, settings.embedding_retry_base_seconds)

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start : start + batch_size]
        texts = [c.chunk_text for c in batch]
        metadatas = [{"chunk_id": c.chunk_id, **c.metadata} for c in batch]
        ids = [c.chunk_id for c in batch]
        _add_texts_with_retry(
            store=store,
            texts=texts,
            metadatas=metadatas,
            ids=ids,
            max_retries=max_retries,
            base_delay=base_delay,
        )
    store.persist()
    return get_collection_name(strategy)


def _is_rate_limit_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "ratelimit" in message or "rate limit" in message or "429" in message


def _add_texts_with_retry(
    *,
    store: Chroma,
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
    max_retries: int,
    base_delay: float,
) -> None:
    attempt = 0
    while True:
        try:
            store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
            return
        except Exception as exc:
            if not _is_rate_limit_error(exc) or attempt >= max_retries:
                raise
            delay_seconds = base_delay * (2**attempt)
            time.sleep(delay_seconds)
            attempt += 1


def query_chroma(
    *,
    strategy: str,
    query: str,
    top_k: int,
    threshold: float | None = None,
    doc_id: str | None = None,
) -> list[QueryResultItem]:
    store = get_vector_store(strategy)
    filter_payload = {"doc_id": doc_id} if doc_id else None
    raw = store.similarity_search_with_score(query=query, k=top_k, filter=filter_payload)

    items: list[QueryResultItem] = []
    for rank, (doc, distance) in enumerate(raw, start=1):
        similarity = 1 - float(distance)
        if threshold is not None and similarity < threshold:
            continue
        items.append(
            QueryResultItem(
                rank=rank,
                chunk_id=str(doc.metadata.get("chunk_id", "")),
                distance=float(distance),
                similarity=similarity,
                text=doc.page_content,
                metadata=doc.metadata,
            )
        )
    return items


def list_chroma_collections() -> list[dict[str, int | str]]:
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    output: list[dict[str, int | str]] = []
    for collection in client.list_collections():
        output.append({"name": collection.name, "count": collection.count()})
    return output


def peek_chroma_collection(
    strategy: str,
    limit: int = 5,
    include_embeddings: bool = False,
) -> dict[str, list]:
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collection = client.get_or_create_collection(name=get_collection_name(strategy))
    if include_embeddings:
        raw = collection.get(
            limit=limit,
            include=["documents", "metadatas", "embeddings"],
        )
    else:
        raw = collection.peek(limit=limit)
    ids_raw = raw.get("ids")
    documents_raw = raw.get("documents")
    metadatas_raw = raw.get("metadatas")
    embeddings_raw = raw.get("embeddings")

    ids = _to_json_list(ids_raw)
    documents = _to_json_list(documents_raw)
    metadatas = _to_json_list(metadatas_raw)
    embeddings = _to_json_list(embeddings_raw)
    embeddings = [e.tolist() if hasattr(e, "tolist") else e for e in embeddings]
    items = []
    for idx, chunk_id in enumerate(ids):
        item = {
            "id": chunk_id,
            "document": documents[idx] if idx < len(documents) else "",
            "metadata": metadatas[idx] if idx < len(metadatas) and metadatas[idx] else {},
        }
        if include_embeddings:
            embedding_value = embeddings[idx] if idx < len(embeddings) else []
            if hasattr(embedding_value, "tolist"):
                embedding_value = embedding_value.tolist()
            item["embedding"] = embedding_value
        items.append(
            item
        )
    return {
        "items": items,
        "ids": ids,
        "documents": documents,
        "metadatas": metadatas,
        "embeddings": embeddings if include_embeddings else [],
    }


def clear_all_chroma_collections() -> dict[str, int | list[str]]:
    Path(settings.chroma_persist_dir).mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    collections = [c.name for c in client.list_collections()]
    for name in collections:
        client.delete_collection(name=name)
    return {"deleted_collections": collections, "deleted_count": len(collections)}
