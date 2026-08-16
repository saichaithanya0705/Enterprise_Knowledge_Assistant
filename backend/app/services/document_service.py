"""Orchestrates the document ingestion pipeline: load -> chunk -> embed -> persist."""
import logging

from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.rag.loaders import load_text, UnsupportedFileType
from app.rag.chunking import chunk_document
from app.rag.embeddings import embed_texts
from app.rag import vector_store
from app.repositories import document_repo
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)


async def ingest_document(db: Session, filename: str, raw_bytes: bytes, category: str = "General"):
    file_type = filename.split(".")[-1].lower()
    doc = document_repo.create_document(db, filename=filename, file_type=file_type, category=category)
    chunk_ids: list[str] = []
    embedding_backend: str | None = None

    try:
        text = load_text(filename, raw_bytes)
        if not text.strip():
            raise ValueError("No extractable text found in the document")

        pieces = chunk_document(text, settings.chunk_size, settings.chunk_overlap)
        vectors, embedding_backend = await embed_texts([p.content for p in pieces], input_type="passage")

        chunk_rows = [
            DocumentChunk(document_id=doc.id, chunk_index=p.index, content=p.content, section=p.section)
            for p in pieces
        ]
        document_repo.add_chunks(db, chunk_rows)
        chunk_ids = [c.id for c in chunk_rows]

        # Index vectors in ChromaDB, keyed by the SQLite chunk id.
        vector_store.upsert_chunks(
            ids=chunk_ids,
            embeddings=vectors,
            documents=[c.content for c in chunk_rows],
            metadatas=[
                {"document_id": doc.id, "filename": filename, "section": c.section or "", "chunk_index": c.chunk_index}
                for c in chunk_rows
            ],
            backend=embedding_backend,
        )

        document_repo.mark_ready(db, doc, char_count=len(text), chunk_count=len(chunk_rows))
        return doc

    except Exception as e:  # noqa: BLE001 - convert to a stored failure state, not a 500
        logger.warning(
            "Document ingestion failed document_id=%s error_type=%s",
            doc.id,
            document_repo._bounded_exception_type(e),
        )
        db.rollback()
        error = (
            document_repo.UNSUPPORTED_DOCUMENT_ERROR
            if isinstance(e, UnsupportedFileType)
            else document_repo.GENERIC_DOCUMENT_ERROR
        )
        if chunk_ids and embedding_backend:
            try:
                vector_store.delete_chunks(chunk_ids, backend=embedding_backend)
            except Exception as cleanup_error:  # noqa: BLE001 - preserve failed state if cleanup itself fails
                logger.warning(
                    "Document vector cleanup failed document_id=%s error_type=%s",
                    doc.id,
                    document_repo._bounded_exception_type(cleanup_error),
                )
                document_repo.add_cleanup_task(
                    db,
                    operation_key=f"ingestion-cleanup:{doc.id}",
                    operation="ingestion_cleanup",
                    document_id=doc.id,
                    chunk_ids=chunk_ids,
                    backend=embedding_backend,
                )
                error = document_repo.CLEANUP_PENDING_DOCUMENT_ERROR
        document_repo.mark_failed(db, doc, error)
        raise


def reconcile_cleanup_tasks(db: Session) -> dict[str, int]:
    """Retry pending vector cleanup once per task; every operation is idempotent."""
    attempted = resolved = pending = 0
    for task in document_repo.list_cleanup_tasks(db):
        attempted += 1
        try:
            if task.operation == "document_delete":
                vector_store.delete_by_document(task.document_id)
                document = document_repo.get_document(db, task.document_id)
                if document is not None:
                    db.delete(document)
            elif task.operation == "ingestion_cleanup":
                vector_store.delete_chunks(
                    document_repo.decode_cleanup_chunk_ids(task),
                    backend=task.backend,
                )
            else:
                raise ValueError("Unknown cleanup operation")
        except Exception as error:  # noqa: BLE001 - retain work for the next operator retry
            document_repo.record_cleanup_failure(db, task, error)
            pending += 1
        else:
            document_repo.remove_cleanup_task(db, task)
            resolved += 1
    return {"attempted": attempted, "resolved": resolved, "pending": pending}
