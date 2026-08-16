"""Pydantic schemas for feedback endpoint."""
from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    message_id: str
    rating: int = Field(..., ge=-1, le=1)
    comment: str | None = None
