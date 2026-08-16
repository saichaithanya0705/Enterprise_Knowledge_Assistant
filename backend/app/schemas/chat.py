"""Pydantic schemas for chat/RAG endpoints."""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: str | None = None
    message: str = Field(..., min_length=1, max_length=4000)


class SourceRef(BaseModel):
    document_id: str
    filename: str
    section: str | None = None
    chunk_id: str
    similarity: float
    excerpt: str


class RetrievedChunkTrace(BaseModel):
    chunk_id: str
    filename: str
    section: str | None = None
    vector_score: float
    bm25_score: float
    fused_score: float
    rerank_score: float
    used_in_context: bool
    excerpt: str


class DebugTrace(BaseModel):
    original_query: str
    improved_query: str
    retrieval_mode: str
    embedding_backend: str
    rerank_backend: str
    retrieved_chunks: list[RetrievedChunkTrace]
    final_context_chunk_ids: list[str]
    prompt_preview: str
    llm_backend: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    sources: list[SourceRef]
    debug: DebugTrace
    grounded: bool


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict] | None = None
    debug: DebugTrace | None = None
    created_at: str
