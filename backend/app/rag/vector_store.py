"""
ChromaDB-backed vector index. This is the single source of truth for chunk
embeddings and semantic search - SQLite holds chunk text/metadata for joins
and display, Chroma holds the vectors and does the actual similarity search.
"""
import chromadb

from app.core.config import get_settings

_client = None
_collection = None


def _ensure_initialized():
    global _client, _collection
    if _collection is not None:
        return
    settings = get_settings()
    _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    _collection = _client.get_or_create_collection(
        name="document_chunks",
        metadata={"hnsw:space": "cosine"},
    )


def reset_for_tests():
    """Drop the cached client/collection so the next call rebuilds against the current settings."""
    global _client, _collection
    _client = None
    _collection = None


def upsert_chunks(ids: list[str], embeddings: list[list[float]], documents: list[str], metadatas: list[dict]) -> None:
    if not ids:
        return
    _ensure_initialized()
    _collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(embedding: list[float], top_k: int, where: dict | None = None) -> list[tuple[str, float]]:
    """Returns [(chunk_id, similarity_0_to_1), ...] ordered by similarity descending."""
    _ensure_initialized()
    if _collection.count() == 0:
        return []
    result = _collection.query(
        query_embeddings=[embedding],
        n_results=min(top_k, _collection.count()),
        where=where,
    )
    ids = result["ids"][0]
    distances = result["distances"][0]  # cosine distance: 0 = identical, 2 = opposite
    return [(cid, max(0.0, 1.0 - dist)) for cid, dist in zip(ids, distances)]


def delete_by_document(document_id: str) -> None:
    _ensure_initialized()
    _collection.delete(where={"document_id": document_id})


def delete_chunks(chunk_ids: list[str]) -> None:
    _ensure_initialized()
    if chunk_ids:
        _collection.delete(ids=chunk_ids)
