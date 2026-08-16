"""Pydantic schemas for document endpoints."""
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    category: str
    status: str
    char_count: int
    chunk_count: int
    error_message: str | None = None
    created_at: datetime


class ChunkPreview(BaseModel):
    id: str
    chunk_index: int
    content: str
    section: str | None = None
