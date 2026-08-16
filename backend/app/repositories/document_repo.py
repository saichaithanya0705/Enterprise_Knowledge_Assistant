"""Data access for documents and chunks."""
from sqlalchemy.orm import Session, joinedload

from app.models.document import Document, DocumentChunk
from app.rag import vector_store


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
    doc.error_message = error
    db.commit()


def add_chunks(db: Session, chunks: list[DocumentChunk]) -> None:
    db.add_all(chunks)
    db.commit()


def list_documents(db: Session) -> list[Document]:
    return db.query(Document).order_by(Document.created_at.desc()).all()


def get_document(db: Session, doc_id: str) -> Document | None:
    return db.query(Document).filter(Document.id == doc_id).first()


def delete_document(db: Session, doc: Document) -> None:
    vector_store.delete_by_document(doc.id)  # keep Chroma in sync with SQLite
    db.delete(doc)
    db.commit()


def list_ready_chunks(db: Session) -> list[DocumentChunk]:
    return (
        db.query(DocumentChunk)
        .join(Document)
        .options(joinedload(DocumentChunk.document))
        .filter(Document.status == "ready")
        .all()
    )
