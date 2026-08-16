"""ChromaDB-backed vector index with model- and dimension-safe generations.

SQLite holds chunk text and metadata. Chroma holds vectors and performs
similarity search. Every embedding model/dimension pair gets its own
collection so provider changes never mix incompatible vectors.
"""
import hashlib
import re
from collections.abc import Callable, Collection

import chromadb

from app.core.config import get_settings

_client = None
_client_path: str | None = None
_collections: dict[str, object] = {}
_OWNED_BACKENDS = ("local_fallback", "nvidia")
_LEGACY_COLLECTION_NAME = "document_chunks"
_GENERATION_PATTERN = re.compile(
    r"^document_chunks_(local_fallback|nvidia)_(\d+)_([0-9a-f]{12})$"
)
_MAX_DELETE_ATTEMPTS = 3
_LOCAL_MODEL_ID = "local-hashing-v1"


def _validate_backend(backend: str) -> str:
    if backend not in _OWNED_BACKENDS:
        raise ValueError(f"Unsupported embedding backend: {backend}")
    return backend


def _validate_dimension(dimension: int) -> int:
    if not isinstance(dimension, int) or dimension <= 0:
        raise ValueError("Embedding dimension must be a positive integer")
    return dimension


def _model_id(backend: str, model_id: str | None = None) -> str:
    _validate_backend(backend)
    if backend == "local_fallback":
        return _LOCAL_MODEL_ID
    return model_id or get_settings().nvidia_embedding_model or "nvidia-unknown-model"


def _model_token(backend: str, model_id: str | None = None) -> str:
    return hashlib.sha256(_model_id(backend, model_id).encode("utf-8")).hexdigest()[:12]


def collection_name(backend: str, dimension: int) -> str:
    """Return a deterministic Chroma-safe name for a model generation."""
    backend = _validate_backend(backend)
    dimension = _validate_dimension(dimension)
    return f"document_chunks_{backend}_{dimension}_{_model_token(backend)}"


def _ensure_client():
    global _client, _client_path, _collections
    path = str(get_settings().chroma_persist_dir)
    if _client is not None and _client_path == path:
        return _client
    _client = chromadb.PersistentClient(path=path)
    _client_path = path
    _collections = {}
    return _client


def _existing_collection_names() -> set[str]:
    client = _ensure_client()
    return {
        item if isinstance(item, str) else item.name
        for item in client.list_collections()
    }


def _collection_for_name(name: str):
    return _ensure_client().get_collection(name=name)


def _get_collection(backend: str, dimension: int, create: bool):
    name = collection_name(backend, dimension)
    client = _ensure_client()
    if name in _collections:
        return _collections[name]

    if not create and name not in _existing_collection_names():
        return None
    if create:
        collection = client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )
    else:
        collection = _collection_for_name(name)
    _collections[name] = collection
    return collection


def _is_managed_collection(name: str, backend: str | None = None) -> bool:
    if name == _LEGACY_COLLECTION_NAME:
        return backend is None
    if name in {f"document_chunks_{item}" for item in _OWNED_BACKENDS}:
        return backend is None or name == f"document_chunks_{backend}"
    match = _GENERATION_PATTERN.fullmatch(name)
    return bool(match and (backend is None or match.group(1) == backend))


def _managed_collection_names(backend: str | None = None) -> list[str]:
    if backend is not None:
        _validate_backend(backend)
    return sorted(
        name
        for name in _existing_collection_names()
        if _is_managed_collection(name, backend=backend)
    )


def _is_transient_cleanup_error(error: Exception) -> bool:
    if isinstance(error, (ConnectionError, TimeoutError, OSError)):
        return True
    text = f"{type(error).__name__} {error}".lower()
    transient_markers = (
        "temporarily", "transient", "timeout", "timed out", "connection",
        "unavailable", "too many requests", "429", "503", "internal server",
    )
    return any(marker in text for marker in transient_markers)


def _with_bounded_cleanup_retries(operation: Callable[[], None]) -> None:
    for attempt in range(1, _MAX_DELETE_ATTEMPTS + 1):
        try:
            operation()
            return
        except Exception as error:  # noqa: BLE001 - classify below for bounded retry
            if attempt == _MAX_DELETE_ATTEMPTS or not _is_transient_cleanup_error(error):
                raise
            # Chroma calls are synchronous. Keep retries bounded and immediate so
            # an async request is never blocked by a sleep-based backoff.
            continue


def reset_for_tests():
    """Drop cached clients and collections so the next call uses current settings."""
    global _client, _client_path, _collections
    _client = None
    _client_path = None
    _collections = {}


def upsert_chunks(
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
    backend: str,
) -> None:
    _validate_backend(backend)
    if not ids:
        return
    if len(ids) != len(embeddings) or len(ids) != len(documents) or len(ids) != len(metadatas):
        raise ValueError("Vector upsert fields must have matching lengths")
    dimensions = {_validate_dimension(len(vector)) for vector in embeddings}
    if len(dimensions) != 1:
        raise ValueError("Vector upsert requires non-empty vectors with one shared dimension")
    dimension = dimensions.pop()
    collection = _get_collection(backend, dimension, create=True)
    collection.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)


def query(
    embedding: list[float], top_k: int, backend: str, where: dict | None = None
) -> list[tuple[str, float]]:
    """Return ``(chunk_id, similarity_0_to_1)`` ordered by similarity."""
    _validate_backend(backend)
    if not embedding or top_k <= 0:
        return []
    dimension = _validate_dimension(len(embedding))
    collection = _get_collection(backend, dimension, create=False)
    if collection is None:
        return []
    count = collection.count()
    if count == 0:
        return []
    query_args = {
        "query_embeddings": [embedding],
        "n_results": min(top_k, count),
    }
    if where is not None:
        query_args["where"] = where
    result = collection.query(**query_args)
    ids = result["ids"][0]
    distances = result["distances"][0]  # cosine distance: 0 = identical, 2 = opposite
    return [(cid, min(1.0, max(0.0, 1.0 - dist))) for cid, dist in zip(ids, distances)]


def _delete_by_document_once(document_id: str) -> None:
    for name in _managed_collection_names():
        _collection_for_name(name).delete(where={"document_id": document_id})


def delete_by_document(document_id: str) -> None:
    """Idempotently delete a document from every current and historical index."""
    _with_bounded_cleanup_retries(lambda: _delete_by_document_once(document_id))


def _delete_chunks_once(chunk_ids: list[str], backend: str | None) -> None:
    for name in _managed_collection_names(backend=backend):
        _collection_for_name(name).delete(ids=chunk_ids)


def delete_chunks(chunk_ids: list[str], backend: str | None = None) -> None:
    if backend is not None:
        _validate_backend(backend)
    if not chunk_ids:
        return
    _with_bounded_cleanup_retries(lambda: _delete_chunks_once(chunk_ids, backend))


def _historical_generation_present(names: set[str], active_model: str | None = None) -> bool:
    generations: dict[tuple[str, str], set[int]] = {}
    for name in names:
        match = _GENERATION_PATTERN.fullmatch(name)
        if not match:
            continue
        backend, dimension, token = match.groups()
        generations.setdefault((backend, token), set()).add(int(dimension))
        expected_token = _model_token(
            backend,
            active_model if backend == "nvidia" else None,
        )
        if token != expected_token:
            return True
    return any(len(dimensions) > 1 for dimensions in generations.values()) or any(
        f"document_chunks_{backend}" in names for backend in _OWNED_BACKENDS
    )


def _collection_has_vectors(name: str) -> bool:
    return _collection_for_name(name).count() > 0


def _collection_chunk_ids(name: str) -> set[str]:
    """Enumerate Chroma IDs without loading documents, embeddings, or metadata."""
    result = _collection_for_name(name).get(include=[])
    ids = result.get("ids")
    if not isinstance(ids, list) or not all(isinstance(item, str) for item in ids):
        raise RuntimeError("Chroma returned invalid collection IDs")
    return set(ids)


def _active_generation_present(
    names: set[str], backend: str, active_model: str | None = None
) -> bool:
    token = _model_token(backend, active_model)
    for name in names:
        match = _GENERATION_PATTERN.fullmatch(name)
        if match and match.group(1) == backend and match.group(3) == token:
            if _collection_has_vectors(name):
                return True
    return False


def _active_generation_names(
    names: set[str], backend: str, active_model: str | None = None
) -> list[str]:
    token = _model_token(backend, active_model)
    return sorted(
        name
        for name in names
        if (match := _GENERATION_PATTERN.fullmatch(name))
        and match.group(1) == backend
        and match.group(3) == token
    )


def _active_generation_chunk_ids(
    names: set[str], backend: str, active_model: str | None = None
) -> tuple[set[str], set[int]]:
    """Return the union for one model token and its dimensions."""
    generation_names = _active_generation_names(names, backend, active_model)
    ids: set[str] = set()
    dimensions: set[int] = set()
    for name in generation_names:
        match = _GENERATION_PATTERN.fullmatch(name)
        assert match is not None
        dimensions.add(int(match.group(2)))
        ids.update(_collection_chunk_ids(name))
    return ids, dimensions


def _unavailable_status(
    reason: str = "index introspection unavailable",
    ready_chunk_count: int | None = None,
) -> dict:
    return {
        "index_status": "unavailable",
        "reingest_required": False,
        "legacy_collections_present": False,
        "historical_generations_present": False,
        "collections": [],
        "ready_chunk_count": ready_chunk_count,
        "active_chunk_count": None,
        "missing_chunk_count": None,
        "status_error": reason,
    }


def lifecycle_status(
    active_backend: str | None = None,
    active_model: str | None = None,
    ready_chunk_ids: Collection[str] | None = None,
) -> dict:
    """Return safe, read-only signals about index generations and reingest needs."""
    ready_count: int | None = None
    try:
        if ready_chunk_ids is None:
            raise RuntimeError("ready chunk metadata unavailable")
        ready_ids = set(ready_chunk_ids)
        ready_count = len(ready_ids)
        names = _existing_collection_names()
        managed_names = sorted(name for name in names if _is_managed_collection(name))
        legacy_present = _LEGACY_COLLECTION_NAME in names
        historical_present = _historical_generation_present(names, active_model=active_model)
        selected_backend = active_backend or (
            "nvidia" if get_settings().nvidia_configured else "local_fallback"
        )
        selected_model = active_model if active_backend is not None else None
        data_present = legacy_present or any(_collection_has_vectors(name) for name in managed_names)
        active_ids, active_dimensions = _active_generation_chunk_ids(
            names, selected_backend, selected_model
        )
        active_present = bool(active_ids)
        coverage_complete = ready_ids.issubset(active_ids)
        multiple_active_dimensions = len(active_dimensions) > 1
        reingest_required = (
            legacy_present
            or historical_present
            or multiple_active_dimensions
            or (ready_ids and not coverage_complete)
            or (data_present and not active_present)
        )
        if reingest_required:
            index_status = "reingest_required"
        elif data_present:
            index_status = "ready"
        else:
            index_status = "empty"
        return {
            "index_status": index_status,
            "reingest_required": reingest_required,
            "legacy_collections_present": legacy_present,
            "historical_generations_present": historical_present,
            "collections": managed_names,
            "ready_chunk_count": len(ready_ids),
            "active_chunk_count": len(active_ids),
            "missing_chunk_count": len(ready_ids - active_ids),
        }
    except Exception:  # noqa: BLE001 - status must never take down the health route
        return _unavailable_status(ready_chunk_count=ready_count)
