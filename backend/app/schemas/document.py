"""Pydantic schemas for document endpoints."""
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, field_validator


DocumentCategory = Literal["HR", "IT", "Finance", "General"]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    filename: str
    file_type: str
    category: DocumentCategory
    status: str
    char_count: int
    chunk_count: int
    error_message: str | None = None
    created_at: datetime

    @field_validator("error_message", mode="before")
    @classmethod
    def sanitize_error_message(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if value in {
            "Unsupported file type. Please upload a supported document.",
            "Document processing failed. Please try again or contact support.",
            "Document processing failed and cleanup is pending. Retry cleanup from system status.",
        }:
            return value
        return "Document processing failed. Please try again or contact support."


class ChunkPreview(BaseModel):
    id: str
    chunk_index: int
    content: str
    section: str | None = None
