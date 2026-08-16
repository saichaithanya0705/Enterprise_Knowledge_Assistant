"""Data access for documents, chunks, and durable vector cleanup work."""
import json
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentChunk, VectorCleanupTask
from app.rag import vector_store


logger = logging.getLogger(__name__)

GENERIC_DOCUMENT_ERROR = "Document processing failed. Please try again or contact support."
UNSUPPORTED_DOCUMENT_ERROR = "Unsupported file type. Please upload a supported document."
CLEANUP_PENDING_DOCUMENT_ERROR = "Document processing failed and cleanup is pending. Retry cleanup from system status."
_USER_SAFE_DOCUMENT_ERRORS = frozenset(
    {GENERIC_DOCUMENT_ERROR, UNSUPPORTED_DOCUMENT_ERROR, CLEANUP_PENDING_DOCUMENT_ERROR}
)


def _bounded_exception_type(error: Exception) -> str:
    return type(error).__name__[:80]


def create_document(db: Session, filename: str, file_type: str, category: str) -> Document:
    doc = Document(filename=filename, file_type=file_type, category=category, status="processing")
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def mark_ready(db: Session, doc: Document, char_count: int, chunk_count: int) -> None:
    doc.status = "ready"
    doc.char_count = char_count
    doc.chunk_count = chunk_count
    db.commit()


def mark_failed(db: Session, doc: Document, error: str) -> None:
    doc.status = "failed"
    doc.error_message = error if error in _USER_SAFE_DOCUMENT_ERRORS else GENERIC_DOCUMENT_ERROR
    db.commit()


def add_chunks(db: Session, chunks: list[DocumentChunk]) -> None:
    db.add_all(chunks)
    db.flush()


def list_documents(db: Session) -> list[Document]:
    return db.query(Document).order_by(Document.created_at.desc()).all()


def get_document(db: Session, doc_id: str) -> Document | None:
    return db.query(Document).filter(Document.id == doc_id).first()


def delete_document(db: Session, doc: Document) -> None:
    chunk_ids = [chunk.id for chunk in doc.chunks]
    try:
        vector_store.delete_by_document(doc.id)  # keep Chroma in sync with SQLite
    except Exception as error:  # noqa: BLE001 - preserve the row for idempotent recovery
        logger.warning(
            "Document vector cleanup failed document_id=%s error_type=%s",
            doc.id,
            _bounded_exception_type(error),
        )
        db.rollback()
        add_cleanup_task(
            db,
            operation_key=f"document-delete:{doc.id}",
            operation="document_delete",
            document_id=doc.id,
            chunk_ids=chunk_ids,
            backend=None,
        )
        doc.status = "failed"
        doc.error_message = CLEANUP_PENDING_DOCUMENT_ERROR
        db.commit()
        raise
    db.delete(doc)
    db.commit()


def add_cleanup_task(
    db: Session,
    *,
    operation_key: str,
    operation: str,
    document_id: str,
    chunk_ids: list[str] | None,
    backend: str | None,
) -> VectorCleanupTask:
    """Add or reuse a pending task without committing its surrounding transaction."""
    task = db.query(VectorCleanupTask).filter(VectorCleanupTask.operation_key == operation_key).first()
    if task is None:
        task = VectorCleanupTask(
            operation_key=operation_key,
            operation=operation,
            document_id=document_id,
            chunk_ids_json=json.dumps(chunk_ids or []),
            backend=backend,
        )
        try:
            with db.begin_nested():
                db.add(task)
                db.flush()
        except IntegrityError:
            # Another transaction may have won the unique-key race. The nested
            # rollback leaves the caller's outer transaction usable.
            task = db.query(VectorCleanupTask).filter(VectorCleanupTask.operation_key == operation_key).first()
            if task is None:
                raise
    return task


def list_cleanup_tasks(db: Session) -> list[VectorCleanupTask]:
    return db.query(VectorCleanupTask).order_by(VectorCleanupTask.created_at.asc()).all()


def pending_cleanup_count(db: Session) -> int:
    return db.query(VectorCleanupTask).count()


def decode_cleanup_chunk_ids(task: VectorCleanupTask) -> list[str]:
    try:
        value = json.loads(task.chunk_ids_json or "[]")
    except (TypeError, ValueError) as error:
        raise ValueError("Stored cleanup task has invalid chunk IDs") from error
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise ValueError("Stored cleanup task has invalid chunk IDs")
    return value


def record_cleanup_failure(db: Session, task: VectorCleanupTask, error: Exception) -> None:
    task.attempts += 1
    task.last_error = f"Cleanup failed: {_bounded_exception_type(error)}"
    task.last_attempt_at = datetime.now(timezone.utc)
    db.commit()


def remove_cleanup_task(db: Session, task: VectorCleanupTask) -> None:
    db.delete(task)
    db.commit()


def list_ready_chunks(db: Session) -> list[DocumentChunk]:
    return (
        db.query(DocumentChunk)
        .join(Document)
        .options(joinedload(DocumentChunk.document))
        .filter(Document.status == "ready")
        .all()
    )


def list_ready_chunk_ids(db: Session) -> list[str]:
    """Return only ready chunk IDs for inexpensive index coverage checks."""
    rows = (
        db.query(DocumentChunk.id)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.status == "ready")
        .all()
    )
    return [row[0] for row in rows]
