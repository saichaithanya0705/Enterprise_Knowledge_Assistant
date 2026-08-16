"""Pydantic schemas for feedback endpoint."""
from typing import Literal

from pydantic import BaseModel, Field


class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal[-1, 1]
    comment: str | None = Field(default=None, max_length=2000)
