"""Orchestrates the full RAG query pipeline for a chat turn."""
from sqlalchemy.orm import Session

from app.repositories import document_repo, conversation_repo
from app.rag.query_improver import improve_query
from app.rag.retriever import hybrid_retrieve
from app.rag.context_builder import build_context, format_context_for_prompt
from app.llm.llm_service import generate_answer
from app.core.config import get_settings

settings = get_settings()


def _history_for_llm(conversation) -> list[dict]:
    return [{"role": m.role, "content": m.content} for m in conversation.messages]


async def answer_question(db: Session, conversation_id: str | None, question: str):
    conversation = conversation_repo.get_or_create_conversation(db, conversation_id, title_hint=question)
    history = _history_for_llm(conversation)

    improved_query = await improve_query(question)

    all_chunks = document_repo.list_ready_chunks(db)
    retrieved, embedding_backend = await hybrid_retrieve(improved_query, all_chunks)
    used_chunks, all_reranked, rerank_backend = await build_context(improved_query, retrieved)
    context_text = format_context_for_prompt(used_chunks)

    conversation_repo.add_message(db, conversation.id, "user", question)

    answer, llm_backend = await generate_answer(context_text, question, history)
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
    debug_trace = {
        "original_query": question,
        "improved_query": improved_query,
        "retrieval_mode": "hybrid_bm25_vector_rrf",
        "embedding_backend": embedding_backend,
        "rerank_backend": rerank_backend,
        "retrieved_chunks": [
            {
                "chunk_id": c.retrieved.chunk.id,
                "filename": c.retrieved.chunk.document.filename,
                "section": c.retrieved.chunk.section,
                "vector_score": round(c.retrieved.vector_score, 4),
                "bm25_score": round(c.retrieved.bm25_score, 4),
                "fused_score": round(c.rerank_score, 4),
                "used_in_context": c.retrieved.chunk.id in used_ids,
                "excerpt": c.retrieved.chunk.content[:160],
            }
            for c in all_reranked
        ],
        "final_context_chunk_ids": list(used_ids),
        "prompt_preview": context_text[:600],
        "llm_backend": llm_backend,
    }

    assistant_msg = conversation_repo.add_message(
        db, conversation.id, "assistant", answer, sources=sources, debug_trace=debug_trace
    )

    return conversation, assistant_msg, answer, sources, debug_trace, grounded