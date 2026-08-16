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
    excerpt: str | None = None


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
    query_rewritten: bool = False
    retrieval_mode: str
    embedding_backend: str
    rerank_backend: str
    processed_at: str | None = None
    timings_ms: dict[str, float] = Field(default_factory=dict)
    retrieved_chunks: list[RetrievedChunkTrace]
    final_context_chunk_ids: list[str]
    prompt_preview: str
    llm_backend: str


class ChatResponse(BaseModel):
    conversation_id: str
    message_id: str
    answer: str
    sources: list[SourceRef]
    debug: DebugTrace | None = None
    grounded: bool


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: str
    deleted_at: str | None = None


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict] | None = None
    debug: DebugTrace | None = None
    created_at: str


class AdminMessageOut(MessageOut):
    """Full-fidelity persisted message returned only by admin endpoints."""


class RestoreRequestCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=1000)


class RestoreRequestOut(BaseModel):
    id: str
    conversation_id: str
    conversation_title: str | None = None
    requested_by: str
    requester_email: str | None = None
    reason: str
    status: str
    resolved_by: str | None = None
    resolution_reason: str | None = None
    requested_at: str
    resolved_at: str | None = None


class RestoreRequestResolve(BaseModel):
    approve: bool
    resolution_reason: str | None = Field(default=None, max_length=1000)
