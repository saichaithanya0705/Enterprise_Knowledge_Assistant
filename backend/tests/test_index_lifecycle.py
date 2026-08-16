"""Regression tests for vector collection lifecycle and ingestion integrity."""
import io
from types import SimpleNamespace

from chromadb.errors import InternalError
import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Query

from app.core.config import get_settings
from app.rag import embeddings, vector_store
from app.rag import retriever


def _reset_vector_store(monkeypatch, tmp_path):
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    get_settings.cache_clear()
    vector_store.reset_for_tests()


def test_local_and_nvidia_vectors_use_dimension_safe_collections(monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path)

    persistent = vector_store._ensure_client()
    legacy = persistent.get_or_create_collection(
        name="document_chunks",
        metadata={"hnsw:space": "cosine"},
    )
    legacy_vector = [0.4] * 256
    legacy.upsert(
        ids=["legacy-chunk"],
        embeddings=[legacy_vector],
        documents=["legacy text"],
        metadatas=[{"document_id": "legacy-doc"}],
    )

    local_vector = [0.1] * 256
    nvidia_vector = [0.2] * 1024
    vector_store.upsert_chunks(
        ["local-chunk"],
        [local_vector],
        ["local text"],
        [{"document_id": "doc-local"}],
        backend="local_fallback",
    )
    vector_store.upsert_chunks(
        ["nvidia-chunk"],
        [nvidia_vector],
        ["nvidia text"],
        [{"document_id": "doc-nvidia"}],
        backend="nvidia",
    )

    assert vector_store.query(local_vector, 1, backend="local_fallback")[0][0] == "local-chunk"
    assert vector_store.query(nvidia_vector, 1, backend="nvidia")[0][0] == "nvidia-chunk"

    assert {collection.name for collection in persistent.list_collections()} >= {
        "document_chunks",
        vector_store.collection_name("local_fallback", 256),
        vector_store.collection_name("nvidia", 1024),
    }
    assert legacy.get(ids=["legacy-chunk"])["ids"] == ["legacy-chunk"]
    assert all(chunk_id != "legacy-chunk" for chunk_id, _ in vector_store.query(local_vector, 10, backend="local_fallback"))


def test_query_of_missing_backend_collection_returns_empty(monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path)

    assert vector_store.query([0.1] * 256, 5, backend="nvidia") == []


def test_truly_empty_index_reports_empty_without_reingest(monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path)

    payload = vector_store.lifecycle_status(active_backend="local_fallback", ready_chunk_ids=set())

    assert payload["index_status"] == "empty"
    assert payload["reingest_required"] is False


def test_unknown_embedding_backend_is_rejected(monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="Unsupported embedding backend"):
        vector_store.query([], 5, backend="unknown")


def test_failed_vector_upsert_leaves_no_chunk_rows_or_vector_ids(client, monkeypatch):
    original_upsert = vector_store.upsert_chunks

    def partial_upsert_then_fail(*args, **kwargs):
        original_upsert(*args, **kwargs)
        raise RuntimeError("index failed after partial write")

    monkeypatch.setattr(vector_store, "upsert_chunks", partial_upsert_then_fail)

    response = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")},
    )

    assert response.status_code == 422
    failed = client.get("/api/documents").json()[0]
    assert failed["status"] == "failed"
    assert client.get(f"/api/documents/{failed['id']}/chunks").json() == []

    vectors, backend = _run(embeddings.embed_texts(["POLICY\nbody"], input_type="passage"))
    assert vector_store.query(vectors[0], 5, backend=backend) == []


def test_document_deletion_removes_vectors_from_every_owned_collection(client):
    document = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")},
    ).json()
    chunk = client.get(f"/api/documents/{document['id']}/chunks").json()[0]
    chunk_id = chunk["id"]

    vector_store.upsert_chunks(
        [chunk_id],
        [[0.3] * 1024],
        [chunk["content"]],
        [{"document_id": document["id"]}],
        backend="nvidia",
    )
    legacy = vector_store._ensure_client().get_or_create_collection(
        name="document_chunks",
        metadata={"hnsw:space": "cosine"},
    )
    legacy.upsert(
        ids=[chunk_id, "legacy-unrelated"],
        embeddings=[[0.4] * 256, [0.5] * 256],
        documents=[chunk["content"], "unrelated legacy text"],
        metadatas=[
            {"document_id": document["id"]},
            {"document_id": "unrelated-document"},
        ],
    )

    assert client.delete(f"/api/documents/{document['id']}").status_code == 204
    assert vector_store.query([0.1] * 256, 5, backend="local_fallback") == []
    assert vector_store.query([0.3] * 1024, 5, backend="nvidia") == []
    assert set(legacy.get(ids=[chunk_id, "legacy-unrelated"])["ids"]) == {"legacy-unrelated"}


def test_system_status_reports_configuration_without_provider_probes(client, monkeypatch):
    from app.api.routes import system as system_module

    monkeypatch.setattr(system_module.settings, "key_gateway_url", "https://gateway.example")
    monkeypatch.setattr(system_module.settings, "key_gateway_api_key", "configured")
    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "configured")

    def unexpected_probe(*args, **kwargs):
        raise AssertionError("system status must not probe configured providers")

    monkeypatch.setattr("app.llm.gateway_client.gateway_client.chat_completion", unexpected_probe)
    monkeypatch.setattr("app.llm.nvidia_client.nvidia_client.embed", unexpected_probe)
    monkeypatch.setattr("app.llm.nvidia_client.nvidia_client.rerank", unexpected_probe)

    payload = client.get("/api/system/status").json()

    assert payload["key_gateway_configured"] is True
    assert payload["nvidia_configured"] is True
    assert payload["chat_backend"] == "configured_unverified"
    assert payload["embedding_backend"] == "configured_unverified"
    assert payload["rerank_backend"] == "configured_unverified"


def test_system_status_reports_local_fallback_when_unconfigured(client):
    payload = client.get("/api/system/status").json()

    assert payload["key_gateway_configured"] is False
    assert payload["nvidia_configured"] is False
    assert payload["chat_backend"] == "local_fallback"
    assert payload["embedding_backend"] == "local_fallback"
    assert payload["rerank_backend"] == "local_fallback"


def test_nvidia_model_and_dimension_generations_do_not_collide(monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path)
    settings = get_settings()
    monkeypatch.setattr(settings, "nvidia_embedding_model", "nvidia/model-a")

    vector_store.upsert_chunks(
        ["nvidia-1024"], [[0.2] * 1024], ["old model"], [{"document_id": "doc-a"}], "nvidia"
    )
    first_name = vector_store.collection_name("nvidia", 1024)

    monkeypatch.setattr(settings, "nvidia_embedding_model", "nvidia/model-b")
    vector_store.upsert_chunks(
        ["nvidia-1536"], [[0.3] * 1536], ["new model"], [{"document_id": "doc-b"}], "nvidia"
    )
    second_name = vector_store.collection_name("nvidia", 1536)

    assert first_name != second_name
    result = vector_store.query([0.3] * 1536, 5, backend="nvidia")
    assert result[0][0] == "nvidia-1536"
    assert result[0][1] == pytest.approx(1.0)
    assert {c.name for c in vector_store._ensure_client().list_collections()} >= {
        first_name,
        second_name,
    }


def test_delete_retries_transient_chroma_failures(monkeypatch):
    calls = []

    class TransientCollection:
        def delete(self, **kwargs):
            calls.append(kwargs)
            if len(calls) < 3:
                raise RuntimeError("temporarily unavailable")

    collection = TransientCollection()
    monkeypatch.setattr(vector_store, "_managed_collection_names", lambda: ["document_chunks_local_fallback_256_deadbeefdead"])
    monkeypatch.setattr(vector_store, "_collection_for_name", lambda name: collection)
    vector_store.delete_by_document("doc-retry")

    assert len(calls) == 3
    assert calls[-1] == {"where": {"document_id": "doc-retry"}}


def test_delete_raises_after_permanent_chroma_failure(monkeypatch):
    calls = []

    class PermanentCollection:
        def delete(self, **kwargs):
            calls.append(kwargs)
            raise ValueError("invalid where clause")

    monkeypatch.setattr(vector_store, "_managed_collection_names", lambda: ["document_chunks_local_fallback_256_deadbeefdead"])
    monkeypatch.setattr(vector_store, "_collection_for_name", lambda name: PermanentCollection())
    with pytest.raises(ValueError, match="invalid where clause"):
        vector_store.delete_by_document("doc-permanent")

    assert len(calls) == 1


def test_delete_chunks_retries_transient_failures(monkeypatch):
    calls = []

    class TransientCollection:
        def delete(self, **kwargs):
            calls.append(kwargs)
            if len(calls) < 3:
                raise ConnectionError("connection reset")

    collection = TransientCollection()
    monkeypatch.setattr(
        vector_store,
        "_managed_collection_names",
        lambda backend=None: ["document_chunks_nvidia_1024_deadbeefdead"],
    )
    monkeypatch.setattr(vector_store, "_collection_for_name", lambda name: collection)
    vector_store.delete_chunks(["chunk-retry"], backend="nvidia")

    assert len(calls) == 3
    assert calls[-1] == {"ids": ["chunk-retry"]}


def test_failed_ingestion_cleanup_error_is_actionable(client, monkeypatch):
    original_upsert = vector_store.upsert_chunks

    def partial_upsert_then_fail(*args, **kwargs):
        original_upsert(*args, **kwargs)
        raise RuntimeError("index failed after partial write")

    monkeypatch.setattr(vector_store, "upsert_chunks", partial_upsert_then_fail)
    monkeypatch.setattr(
        vector_store,
        "delete_chunks",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("storage unavailable")),
    )

    response = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")},
    )

    assert response.status_code == 422
    failed = client.get("/api/documents").json()[0]
    assert failed["status"] == "failed"
    assert failed["error_message"] == (
        "Document processing failed and cleanup is pending. Retry cleanup from system status."
    )


def test_document_delete_preserves_sql_row_when_vector_cleanup_fails(client, monkeypatch):
    document = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")},
    ).json()
    monkeypatch.setattr(
        vector_store,
        "delete_by_document",
        lambda _: (_ for _ in ()).throw(ValueError("permanent cleanup failure")),
    )

    with pytest.raises(ValueError, match="permanent cleanup failure"):
        client.delete(f"/api/documents/{document['id']}")
    assert any(item["id"] == document["id"] for item in client.get("/api/documents").json())


def test_retrieval_degrades_to_bm25_when_chroma_is_unavailable(monkeypatch):
    chunks = [
        SimpleNamespace(id="chunk-1", content="leave policy"),
        SimpleNamespace(id="chunk-2", content="travel policy"),
    ]
    monkeypatch.setattr(retriever, "embed_texts", lambda *args, **kwargs: _async_value(([[0.1] * 256], "local_fallback")))
    monkeypatch.setattr(
        retriever.vector_store,
        "query",
        lambda *args, **kwargs: (_ for _ in ()).throw(InternalError("temporarily unavailable")),
    )

    results, backend = _run(retriever.hybrid_retrieve("leave", chunks, top_k=2))

    assert backend == "local_fallback_chroma_unavailable"
    assert results[0].chunk.id == "chunk-1"
    assert all(result.vector_score == 0.0 for result in results)


def test_retrieval_propagates_unexpected_vector_errors(monkeypatch):
    chunks = [SimpleNamespace(id="chunk-1", content="leave policy")]
    monkeypatch.setattr(retriever, "embed_texts", lambda *args, **kwargs: _async_value(([[0.1] * 256], "local_fallback")))
    monkeypatch.setattr(
        retriever.vector_store,
        "query",
        lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("invalid vector shape")),
    )

    with pytest.raises(ValueError, match="invalid vector shape"):
        _run(retriever.hybrid_retrieve("leave", chunks, top_k=1))


def test_backend_switch_requires_reingest_when_active_generation_is_absent(client, monkeypatch):
    from app.api.routes import system as system_module

    vector_store.upsert_chunks(
        ["local-only"], [[0.1] * 256], ["local text"], [{"document_id": "doc-local"}], "local_fallback"
    )
    assert client.get("/api/system/status").json()["index_status"] == "ready"

    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "configured")
    payload = client.get("/api/system/status").json()

    assert payload["embedding_backend"] == "configured_unverified"
    assert payload["index_status"] == "reingest_required"
    assert payload["index"]["reingest_required"] is True


def test_reverse_backend_switch_requires_reingest_when_local_generation_is_absent(client, monkeypatch):
    from app.api.routes import system as system_module

    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "configured")
    vector_store.upsert_chunks(
        ["nvidia-only"], [[0.1] * 1024], ["nvidia text"], [{"document_id": "doc-nvidia"}], "nvidia"
    )
    assert client.get("/api/system/status").json()["index_status"] == "ready"

    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "")
    payload = client.get("/api/system/status").json()
    assert payload["embedding_backend"] == "local_fallback"
    assert payload["index_status"] == "reingest_required"


def test_failed_ingestion_cleanup_is_persisted_and_reconciled(client, monkeypatch):
    from app.models.document import VectorCleanupTask
    from app.db.database import SessionLocal

    original_upsert = vector_store.upsert_chunks

    def partial_upsert_then_fail(*args, **kwargs):
        original_upsert(*args, **kwargs)
        raise RuntimeError("index failed after partial write")

    monkeypatch.setattr(vector_store, "upsert_chunks", partial_upsert_then_fail)
    monkeypatch.setattr(
        vector_store,
        "delete_chunks",
        lambda *args, **kwargs: (_ for _ in ()).throw(ConnectionError("storage unavailable")),
    )
    response = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")},
    )
    assert response.status_code == 422

    db = SessionLocal()
    try:
        assert db.query(VectorCleanupTask).count() == 1
    finally:
        db.close()

    status = client.get("/api/system/status").json()
    assert status["pending_cleanup_count"] == 1
    assert status["cleanup_action"] == "POST /api/system/index/reconcile"

    monkeypatch.setattr(vector_store, "delete_chunks", lambda *args, **kwargs: None)
    reconcile = client.post("/api/system/index/reconcile")
    assert reconcile.status_code == 200
    assert reconcile.json()["resolved"] == 1

    db = SessionLocal()
    try:
        assert db.query(VectorCleanupTask).count() == 0
    finally:
        db.close()


def test_cleanup_reconciliation_retains_failed_task_and_increments_attempts(client, monkeypatch):
    from app.models.document import VectorCleanupTask
    from app.db.database import SessionLocal

    document = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")},
    ).json()
    monkeypatch.setattr(
        vector_store,
        "delete_by_document",
        lambda _: (_ for _ in ()).throw(ConnectionError("storage unavailable")),
    )
    with pytest.raises(ConnectionError):
        client.delete(f"/api/documents/{document['id']}")

    db = SessionLocal()
    try:
        task = db.query(VectorCleanupTask).one()
        assert task.attempts == 0
    finally:
        db.close()

    response = client.post("/api/system/index/reconcile")
    assert response.status_code == 200
    assert response.json()["pending"] == 1

    db = SessionLocal()
    try:
        task = db.query(VectorCleanupTask).one()
        assert task.attempts == 1
        assert task.last_error == "Cleanup failed: ConnectionError"
    finally:
        db.close()

    monkeypatch.setattr(vector_store, "delete_by_document", lambda _: None)
    response = client.post("/api/system/index/reconcile")
    assert response.json()["resolved"] == 1
    assert client.get(f"/api/documents/{document['id']}/chunks").status_code == 404


def test_query_counts_chroma_collection_once(monkeypatch):
    class CountedCollection:
        def __init__(self):
            self.count_calls = 0

        def count(self):
            self.count_calls += 1
            return 1

        def query(self, **kwargs):
            assert kwargs["n_results"] == 1
            return {"ids": [["chunk-1"]], "distances": [[0.0]]}

    collection = CountedCollection()
    monkeypatch.setattr(vector_store, "_get_collection", lambda *args, **kwargs: collection)

    assert vector_store.query([0.1] * 256, 5, backend="local_fallback") == [("chunk-1", 1.0)]
    assert collection.count_calls == 1


def test_system_status_exposes_reingest_signal_for_old_index_generations(client, monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path)
    vector_store._ensure_client().get_or_create_collection(
        name="document_chunks", metadata={"hnsw:space": "cosine"}
    )

    payload = client.get("/api/system/status").json()

    assert payload["index"]["reingest_required"] is True
    assert payload["index"]["legacy_collections_present"] is True
    assert payload["reingest_required"] is True


def test_system_status_fails_safe_when_index_introspection_fails(client, monkeypatch):
    monkeypatch.setattr(
        vector_store,
        "_existing_collection_names",
        lambda: (_ for _ in ()).throw(RuntimeError("chroma unavailable")),
    )

    response = client.get("/api/system/status")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["index_status"] == "unavailable"
    assert response.json()["index"]["status_error"] == "index introspection unavailable"


def test_system_status_degrades_when_cleanup_metadata_is_unavailable(client, monkeypatch):
    from app.api.routes import system as system_module

    def unavailable(_db):
        raise RuntimeError("cleanup database unavailable")

    monkeypatch.setattr(system_module.document_repo, "pending_cleanup_count", unavailable)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["pending_cleanup_count"] is None
    assert payload["cleanup_metadata_status"] == "unavailable"
    assert payload["cleanup_action"] is None


def _ready_document_chunk_ids(client, content):
    response = client.post(
        "/api/documents",
        files={"file": ("policy.txt", io.BytesIO(content.encode()), "text/plain")},
    )
    assert response.status_code == 201
    document = response.json()
    chunks = client.get(f"/api/documents/{document['id']}/chunks")
    assert chunks.status_code == 200
    return [chunk["id"] for chunk in chunks.json()]


def test_partial_active_generation_requires_reingest_even_when_other_indexes_cover_all_chunks(
    client, monkeypatch
):
    from app.api.routes import system as system_module

    chunk_ids = _ready_document_chunk_ids(client, "first policy") + _ready_document_chunk_ids(
        client, "second policy"
    )
    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "configured")
    vector_store.upsert_chunks(
        chunk_ids[:1],
        [[0.2] * 1024],
        ["first policy"],
        [{"document_id": "partial-doc"}],
        backend="nvidia",
    )

    payload = client.get("/api/system/status").json()

    assert payload["status"] == "degraded"
    assert payload["index_status"] == "reingest_required"
    assert payload["index"]["ready_chunk_count"] == 2
    assert payload["index"]["active_chunk_count"] == 1
    assert payload["index"]["missing_chunk_count"] == 1
    assert "ready_chunk_ids" not in str(payload)


def test_full_active_generation_is_ready_when_every_ready_chunk_is_indexed(client, monkeypatch):
    from app.api.routes import system as system_module

    chunk_ids = _ready_document_chunk_ids(client, "first policy") + _ready_document_chunk_ids(
        client, "second policy"
    )
    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "configured")
    vector_store.upsert_chunks(
        chunk_ids,
        [[0.2] * 1024 for _ in chunk_ids],
        ["policy" for _ in chunk_ids],
        [{"document_id": "complete-doc"} for _ in chunk_ids],
        backend="nvidia",
    )

    payload = client.get("/api/system/status").json()

    assert payload["status"] == "ok"
    assert payload["index_status"] == "ready"
    assert payload["index"]["ready_chunk_count"] == 2
    assert payload["index"]["active_chunk_count"] == 2
    assert payload["index"]["missing_chunk_count"] == 0


def test_system_status_is_unavailable_when_ready_chunk_metadata_fails(client, monkeypatch):
    from app.api.routes import system as system_module

    def unavailable(_db):
        raise RuntimeError("sqlite metadata unavailable")

    monkeypatch.setattr(system_module.document_repo, "list_ready_chunk_ids", unavailable)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["index_status"] == "unavailable"
    assert payload["index"]["ready_chunk_count"] is None
    assert payload["index"]["active_chunk_count"] is None
    assert payload["index"]["missing_chunk_count"] is None


def test_system_status_is_unavailable_when_active_id_enumeration_fails(client, monkeypatch):
    from app.api.routes import system as system_module

    chunk_ids = _ready_document_chunk_ids(client, "first policy")
    monkeypatch.setattr(system_module.settings, "nvidia_api_key", "configured")
    vector_store.upsert_chunks(
        chunk_ids,
        [[0.2] * 1024 for _ in chunk_ids],
        ["first policy" for _ in chunk_ids],
        [{"document_id": "broken-id-doc"} for _ in chunk_ids],
        backend="nvidia",
    )

    def broken_ids(_name):
        raise RuntimeError("chroma metadata unavailable")

    monkeypatch.setattr(vector_store, "_collection_chunk_ids", broken_ids)

    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "degraded"
    assert payload["index_status"] == "unavailable"
    assert payload["index"]["ready_chunk_count"] == 1
    assert payload["index"]["active_chunk_count"] is None


def test_chroma_client_cache_follows_changed_persist_path(monkeypatch, tmp_path):
    _reset_vector_store(monkeypatch, tmp_path / "first")
    vector_store.upsert_chunks(
        ["first"], [[0.1] * 256], ["first"], [{"document_id": "doc-first"}], "local_fallback"
    )

    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "second" / "chroma"))
    get_settings.cache_clear()

    assert vector_store.query([0.1] * 256, 5, backend="local_fallback") == []


def test_cleanup_task_race_recovers_existing_row_without_losing_outer_transaction(client, monkeypatch):
    from app.db import database
    from app.db.database import SessionLocal
    from app.models.document import Document, VectorCleanupTask
    from app.repositories import document_repo

    database.init_db()
    db = SessionLocal()
    try:
        existing = VectorCleanupTask(
            operation_key="ingestion-cleanup:race",
            operation="ingestion_cleanup",
            document_id="document-race",
            chunk_ids_json="[]",
            backend="local_fallback",
        )
        db.add(existing)
        db.commit()

        outer_document = Document(filename="race.txt", file_type="txt", category="General")
        db.add(outer_document)
        db.flush()

        real_first = Query.first
        lookup_count = 0

        def hide_first_racing_lookup(query):
            nonlocal lookup_count
            entity = query.column_descriptions[0].get("entity")
            if entity is VectorCleanupTask and lookup_count == 0:
                lookup_count += 1
                return None
            return real_first(query)

        monkeypatch.setattr(Query, "first", hide_first_racing_lookup)
        real_flush = db.flush
        flush_count = 0

        def raise_duplicate_once(*args, **kwargs):
            nonlocal flush_count
            if flush_count == 0:
                flush_count += 1
                raise IntegrityError("INSERT", {}, RuntimeError("duplicate operation key"))
            return real_flush(*args, **kwargs)

        monkeypatch.setattr(db, "flush", raise_duplicate_once)

        task = document_repo.add_cleanup_task(
            db,
            operation_key="ingestion-cleanup:race",
            operation="ingestion_cleanup",
            document_id="document-race",
            chunk_ids=["chunk-race"],
            backend="local_fallback",
        )
        outer_document.status = "failed"
        db.commit()

        assert task.id == existing.id
        assert db.get(Document, outer_document.id).status == "failed"
        assert db.query(VectorCleanupTask).filter_by(operation_key="ingestion-cleanup:race").count() == 1
    finally:
        db.close()


async def _async_value(value):
    return value


def _run(awaitable):
    import asyncio

    return asyncio.run(awaitable)
