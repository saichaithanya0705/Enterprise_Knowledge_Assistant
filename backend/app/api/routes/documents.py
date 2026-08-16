"""Document upload, listing, and deletion endpoints."""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.repositories import document_repo
from app.services.document_service import ingest_document
from app.schemas.document import DocumentOut, ChunkPreview
from app.rag.loaders import UnsupportedFileType

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "md"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return document_repo.list_documents(db)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...), category: str = Form("General"), db: Session = Depends(get_db)
):
    ext = file.filename.split(".")[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported file type '.{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}")

    raw = await file.read()
    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(400, "File exceeds 10MB limit")

    try:
        doc = await ingest_document(db, file.filename, raw, category)
    except UnsupportedFileType as e:
        raise HTTPException(400, str(e))
    except Exception as e:  # noqa: BLE001
        raise HTTPException(422, f"Could not process document: {e}")

    return doc


@router.get("/{doc_id}/chunks", response_model=list[ChunkPreview])
def get_document_chunks(doc_id: str, db: Session = Depends(get_db)):
    doc = document_repo.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return sorted(doc.chunks, key=lambda c: c.chunk_index)


@router.delete("/{doc_id}", status_code=204)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = document_repo.get_document(db, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    document_repo.delete_document(db, doc)
