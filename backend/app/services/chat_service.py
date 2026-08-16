"""Orchestrates the full RAG query pipeline for a chat turn."""
import asyncio
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.repositories import document_repo, conversation_repo
from app.rag.query_improver import improve_query
from app.rag.retriever import hybrid_retrieve
from app.rag.context_builder import build_context, format_context_for_prompt
from app.llm.llm_service import generate_answer
from app.core.config import get_settings
from app.prompts.templates import build_chat_messages, build_prompt_preview

settings = get_settings()


class _TurnLockEntry:
    def __init__(self):
        self.lock = asyncio.Lock()
        self.references = 0


class _ConversationTurnLocks:
    """Small, reference-counted in-process lock registry for active turns."""

    def __init__(self):
        self._entries: dict[str, _TurnLockEntry] = {}

    @asynccontextmanager
    async def hold(self, conversation_id: str):
        entry = self._entries.get(conversation_id)
        if entry is None:
            entry = _TurnLockEntry()
            self._entries[conversation_id] = entry
        entry.references += 1
        acquired = False
        try:
            await entry.lock.acquire()
            acquired = True
            yield
        finally:
            if acquired:
                entry.lock.release()
            entry.references -= 1
            if entry.references == 0 and self._entries.get(conversation_id) is entry:
                self._entries.pop(conversation_id, None)


_TURN_LOCKS = _ConversationTurnLocks()


def _history_for_llm(conversation) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in conversation.messages]


async def answer_question(
    db: Session,
    conversation_id: str | None,
    question: str,
    user_id: str | None = None,
):
    if conversation_id is not None:
        async with _TURN_LOCKS.hold(conversation_id):
            return await _answer_turn(db, conversation_id, question, user_id)
    return await _answer_turn(db, None, question, user_id)


async def _answer_turn(
    db: Session,
    conversation_id: str | None,
    question: str,
    user_id: str | None,
):
    processed_at = datetime.now(timezone.utc).isoformat()
    stage_started = time.perf_counter()
    timings_ms: dict[str, float] = {}

    def mark(label: str) -> None:
        nonlocal stage_started
        now = time.perf_counter()
        timings_ms[label] = round((now - stage_started) * 1000, 1)
        stage_started = now

    conversation = conversation_repo.get_or_create_conversation(
        db,
        conversation_id,
        title_hint=question,
        user_id=user_id,
    )
    history = _history_for_llm(conversation)

    all_chunks = document_repo.list_ready_chunks(db)
    improved_query = await improve_query(question) if all_chunks else question.strip()
    mark("query_rewrite_ms")
    retrieved, embedding_backend = await hybrid_retrieve(improved_query, all_chunks)
    mark("retrieval_ms")
    used_chunks, all_reranked, rerank_backend = await build_context(improved_query, retrieved)
    mark("rerank_ms")
    context_text = format_context_for_prompt(used_chunks)
    prompt_messages = build_chat_messages(context_text, question, history)

    # All database work before this point is read-only. End the implicit
    # SQLite read transaction before the provider call; the final user and
    # assistant writes happen together only after a successful answer.
    if db is not None:
        db.rollback()
    answer, llm_backend = await generate_answer(
        context_text,
        question,
        history,
        prepared_messages=prompt_messages,
    )
    mark("generation_ms")
    timings_ms["total_ms"] = round(sum(timings_ms.values()), 1)
    grounded = bool(used_chunks)

    sources = [
        {
            "document_id": c.retrieved.chunk.document_id,
            "filename": c.retrieved.chunk.document.filename,
            "section": c.retrieved.chunk.section,
            "chunk_id": c.retrieved.chunk.id,
            # Show the final reranked/fused relevance score, not the raw
            # vector-only leg - a chunk can score 0 on vector_score alone
            # (e.g. surfaced via BM25, or absent from Chroma's candidate
            # set) while still being a strong, correctly-cited source.
            "similarity": round(c.rerank_score, 4),
            "excerpt": c.retrieved.chunk.content[:220],
        }
        for c in used_chunks
    ]

    used_ids = {c.retrieved.chunk.id for c in used_chunks}
    final_context_chunk_ids = [c.retrieved.chunk.id for c in used_chunks]
    prompt_preview = build_prompt_preview(
        prompt_messages,
        context=context_text,
        question=question,
    )
    debug_trace = {
        "original_query": question,
        "improved_query": improved_query,
        "query_rewritten": improved_query.strip().casefold() != question.strip().casefold(),
        "retrieval_mode": "hybrid_bm25_vector_rrf",
        "embedding_backend": embedding_backend,
        "rerank_backend": rerank_backend,
        "processed_at": processed_at,
        "timings_ms": timings_ms,
        "retrieved_chunks": [
            {
                "chunk_id": c.retrieved.chunk.id,
                "filename": c.retrieved.chunk.document.filename,
                "section": c.retrieved.chunk.section,
                "vector_score": round(c.retrieved.vector_score, 4),
                "bm25_score": round(c.retrieved.bm25_score, 4),
                "fused_score": round(c.retrieved.fused_score, 4),
                "rerank_score": round(c.rerank_score, 4),
                "used_in_context": c.retrieved.chunk.id in used_ids,
                "excerpt": c.retrieved.chunk.content[:160],
            }
            for c in all_reranked
        ],
        "final_context_chunk_ids": final_context_chunk_ids,
        "prompt_preview": prompt_preview,
        "llm_backend": llm_backend,
    }

    persisted_conversation, assistant_msg = conversation_repo.add_turn(
        db,
        conversation,
        question,
        answer,
        sources=sources,
        debug_trace=debug_trace,
    )

    return persisted_conversation, assistant_msg, answer, sources, debug_trace, grounded
