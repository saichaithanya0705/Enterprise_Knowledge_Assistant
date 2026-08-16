"""Health check and system status for configured backends and index health."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.database import get_db
from app.rag import vector_store
from app.repositories import document_repo
from app.services.document_service import reconcile_cleanup_tasks

router = APIRouter(prefix="/api/system", tags=["system"])
settings = get_settings()


@router.get("/status")
def status(db: Session = Depends(get_db)):
    chat_backend = "configured_unverified" if settings.key_gateway_configured else "local_fallback"
    embedding_backend = "configured_unverified" if settings.nvidia_configured else "local_fallback"
    ready_metadata_status = "available"
    try:
        ready_chunk_ids = document_repo.list_ready_chunk_ids(db)
    except Exception:  # noqa: BLE001 - status must fail closed if SQLite metadata is unavailable
        ready_chunk_ids = None
        ready_metadata_status = "unavailable"
    index = vector_store.lifecycle_status(
        active_backend="nvidia" if settings.nvidia_configured else "local_fallback",
        active_model=settings.nvidia_embedding_model if settings.nvidia_configured else None,
        ready_chunk_ids=ready_chunk_ids,
    )
    cleanup_metadata_status = "available"
    try:
        pending_cleanup = document_repo.pending_cleanup_count(db)
    except Exception:  # noqa: BLE001 - status remains safe if cleanup metadata is unavailable
        pending_cleanup = None
        cleanup_metadata_status = "unavailable"
    return {
        "status": "degraded"
        if index["index_status"] in {"unavailable", "reingest_required"}
        or pending_cleanup is None
        or pending_cleanup > 0
        else "ok",
        "key_gateway_configured": settings.key_gateway_configured,
        "nvidia_configured": settings.nvidia_configured,
        "chat_backend": chat_backend,
        "embedding_backend": embedding_backend,
        "rerank_backend": embedding_backend,
        "chat_model": settings.key_gateway_chat_model if settings.key_gateway_configured else "local_fallback (extractive)",
        "embedding_model": settings.nvidia_embedding_model if settings.nvidia_configured else "local_fallback (hashing)",
        "rerank_model": settings.nvidia_rerank_model if settings.nvidia_configured else "local_fallback (lexical overlap)",
        "vector_store": "chromadb",
        "index": index,
        "index_status": index["index_status"],
        "reingest_required": index["reingest_required"],
        "legacy_collections_present": index["legacy_collections_present"],
        "historical_generations_present": index["historical_generations_present"],
        "ready_chunk_count": index["ready_chunk_count"],
        "active_chunk_count": index["active_chunk_count"],
        "missing_chunk_count": index["missing_chunk_count"],
        "ready_metadata_status": ready_metadata_status,
        "pending_cleanup_count": pending_cleanup,
        "cleanup_metadata_status": cleanup_metadata_status,
        "cleanup_action": "POST /api/system/index/reconcile" if pending_cleanup else None,
    }


@router.post("/index/reconcile")
def reconcile_index(db: Session = Depends(get_db)):
    return reconcile_cleanup_tasks(db)
