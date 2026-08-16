"""
Turns raw retrieved chunks into a clean, LLM-ready context: reranking,
relevance filtering, deduplication, and size limiting.
"""
import logging
import math
import re
from dataclasses import dataclass

import httpx

from app.core.config import get_settings
from app.rag.retriever import RetrievedChunk, _STOPWORDS
from app.llm.nvidia_client import nvidia_client, NvidiaApiError

logger = logging.getLogger(__name__)

settings = get_settings()


@dataclass
class ContextChunk:
    retrieved: RetrievedChunk
    rerank_score: float


def _stable_sigmoid(logit: float) -> float:
    if logit >= 0:
        scale = math.exp(-logit)
        return 1.0 / (1.0 + scale)
    scale = math.exp(logit)
    return scale / (1.0 + scale)


def _term_overlap_boost(query: str, content: str) -> float:
    """Cheap lexical signal used only as a fallback reranker: fraction of
    meaningful query terms present verbatim in the chunk.

    Requires at least 2 distinct term hits (when the query has 2+ meaningful
    terms to begin with) before counting any overlap at all. A single shared
    word is not real evidence of relevance - it's very easy for one common,
    perfectly legitimate word (e.g. "connection", "access", "request") to
    coincidentally appear in both an unrelated query and an unrelated chunk.
    Blacklisting individual words as they're discovered doesn't scale, since
    almost any word can be the accidental one; requiring corroboration from
    a second term is what actually distinguishes a real topical match from
    noise, without needing to guess every possible incidental word in
    advance.
    """
    words = re.findall(r"[a-z0-9]+", query.lower())
    query_terms = {w for w in words if len(w) > 2 and w not in _STOPWORDS}
    if not query_terms:
        return 0.0
    content_lower = content.lower()
    hits = sum(1 for t in query_terms if t in content_lower)
    if len(query_terms) >= 2 and hits < 2:
        return 0.0
    return hits / len(query_terms)


def _lexical_rerank(query: str, retrieved: list[RetrievedChunk]) -> list[ContextChunk]:
    """
    fused_score is normalized against the *best* candidate in this query's
    own result set (see retriever._rrf_fuse), so the top-ranked chunk always
    scores ~1.0 even when the whole batch is irrelevant to the query - it's a
    relative ranking, not an absolute relevance signal. Term overlap is the
    only real absolute signal this fallback has (no cross-encoder model), so
    it's used as a multiplicative gate rather than a small additive term:
    zero keyword overlap collapses the score toward zero instead of being
    propped up by an artificially-inflated fused_score.
    """
    scored = []
    for r in retrieved:
        overlap = _term_overlap_boost(query, r.chunk.content)
        rerank_score = r.fused_score * overlap
        scored.append(ContextChunk(retrieved=r, rerank_score=rerank_score))
    return sorted(scored, key=lambda c: c.rerank_score, reverse=True)


async def rerank(query: str, retrieved: list[RetrievedChunk]) -> tuple[list[ContextChunk], str]:
    """
    Reranks retrieved candidates. Uses the NVIDIA cross-encoder reranking
    model (nv-rerankqa) when configured - this is a real second-stage
    reranker, distinct from the RRF fusion that produced the candidate set.
    Falls back to a lexical overlap heuristic otherwise.
    Returns (ranked_chunks, backend_used).
    """
    if not retrieved:
        return [], "n/a"

    if nvidia_client.configured:
        try:
            passages = [r.chunk.content for r in retrieved]
            scores = await nvidia_client.rerank(query, passages)
            # NVIDIA logits aren't bounded 0-1 - squash with a stable sigmoid so
            # extreme finite logits cannot overflow.
            scored = [
                ContextChunk(retrieved=r, rerank_score=_stable_sigmoid(s))
                for r, s in zip(retrieved, scores)
            ]
            return sorted(scored, key=lambda c: c.rerank_score, reverse=True), "nvidia"
        except (NvidiaApiError, httpx.HTTPError) as e:
            # Don't let a reranker outage/misconfiguration (e.g. a bad or
            # retired endpoint URL returning 404) take down the whole chat
            # request - fall back to the local lexical reranker instead.
            logger.warning("NVIDIA rerank failed, falling back to local reranker: %s", e)

    return _lexical_rerank(query, retrieved), "local_fallback"


def _is_near_duplicate(a: str, b: str) -> bool:
    a_words, b_words = set(a.lower().split()), set(b.lower().split())
    if not a_words or not b_words:
        return False
    overlap = len(a_words & b_words) / len(a_words | b_words)
    return overlap > 0.85


async def build_context(
    query: str, retrieved: list[RetrievedChunk], threshold: float | None = None, max_chunks: int | None = None
) -> tuple[list[ContextChunk], list[ContextChunk], str]:
    """
    Returns (used_chunks, all_reranked_chunks, rerank_backend). used_chunks is
    the final, deduplicated, relevance-filtered, size-limited context sent to
    the LLM.
    """
    threshold = threshold if threshold is not None else settings.similarity_threshold
    max_chunks = max_chunks or settings.top_k_final_context

    reranked, rerank_backend = await rerank(query, retrieved)
    # No forced top-1 fallback here: if nothing clears the threshold, the
    # query (e.g. small talk like "good morning") isn't actually answerable
    # from the knowledge base, and used_chunks should be empty - forcing a
    # weak top match through as "relevant" fabricates grounding and sources
    # for content that has nothing to do with the question.
    relevant = [c for c in reranked if c.rerank_score >= threshold]

    used: list[ContextChunk] = []
    for c in relevant:
        if any(_is_near_duplicate(c.retrieved.chunk.content, u.retrieved.chunk.content) for u in used):
            continue
        used.append(c)
        if len(used) >= max_chunks:
            break

    return used, reranked, rerank_backend


def format_context_for_prompt(used: list[ContextChunk]) -> str:
    blocks = []
    for i, c in enumerate(used, start=1):
        chunk = c.retrieved.chunk
        label = f"[{i}] {chunk.document.filename}" + (f" - {chunk.section}" if chunk.section else "")
        blocks.append(f"{label}\n{chunk.content}")
    return "\n\n---\n\n".join(blocks)
