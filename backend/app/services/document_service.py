"""Orchestrates the document ingestion pipeline: load -> chunk -> embed -> persist."""
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.rag.loaders import load_text, UnsupportedFileType
from app.rag.chunking import chunk_document
from app.rag.embeddings import embed_texts
from app.rag import vector_store
from app.repositories import document_repo
from app.core.config import get_settings

settings = get_settings()


async def ingest_document(db: Session, filename: str, raw_bytes: bytes, category: str = "General"):
    file_type = filename.split(".")[-1].lower()
    doc = document_repo.create_document(db, filename=filename, file_type=file_type, category=category)

    try:
        text = load_text(filename, raw_bytes)
        if not text.strip():
            raise ValueError("No extractable text found in the document")

        pieces = chunk_document(text, settings.chunk_size, settings.chunk_overlap)
        vectors, _backend = await embed_texts([p.content for p in pieces], input_type="passage")

        chunk_rows = [
            DocumentChunk(document_id=doc.id, chunk_index=p.index, content=p.content, section=p.section)
            for p in pieces
        ]
        document_repo.add_chunks(db, chunk_rows)

        # Index vectors in ChromaDB, keyed by the SQLite chunk id.
        vector_store.upsert_chunks(
            ids=[c.id for c in chunk_rows],
            embeddings=vectors,
            documents=[c.content for c in chunk_rows],
            metadatas=[
                {"document_id": doc.id, "filename": filename, "section": c.section or "", "chunk_index": c.chunk_index}
                for c in chunk_rows
            ],
        )

        document_repo.mark_ready(db, doc, char_count=len(text), chunk_count=len(chunk_rows))
        return doc

    except UnsupportedFileType as e:
        document_repo.mark_failed(db, doc, str(e))
        raise
    except Exception as e:  # noqa: BLE001 - convert to a stored failure state, not a 500
        document_repo.mark_failed(db, doc, f"Ingestion failed: {e}")
        raise
