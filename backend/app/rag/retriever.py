"""
Hybrid retrieval: BM25 keyword search over SQLite chunk text + ChromaDB
vector semantic search, fused with Reciprocal Rank Fusion (RRF).

Kept independent of the API layer - routes call into this module, never
the other way around.
"""
import logging
import math
import re
from dataclasses import dataclass

from chromadb.errors import InternalError, RateLimitError
from rank_bm25 import BM25Okapi

from app.models.document import DocumentChunk
from app.rag.embeddings import embed_texts
from app.rag import vector_store
from app.core.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)
_VECTOR_AVAILABILITY_ERRORS = (InternalError, RateLimitError, ConnectionError, TimeoutError, OSError)

# Common English stopwords, dropped before BM25 scoring so they don't
# inflate matches on short chunks that just happen to share "how"/"do"/"my".
_STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her",
    "its", "our", "their", "this", "that", "these", "those", "and", "or",
    "but", "if", "so", "to", "of", "in", "on", "for", "with", "at", "by",
    "from", "as", "do", "does", "did", "how", "what", "when", "where",
    "who", "why", "can", "could", "will", "would", "should", "get", "got",
    # Generic connector/filler verbs and phrases that carry no topical
    # meaning on their own but commonly appear in both unrelated queries
    # and unrelated documents (e.g. "give me about X" vs. "questions
    # about Y") - without these, a single shared filler word can make an
    # entirely irrelevant chunk look like a real keyword match in the
    # local fallback reranker's term-overlap score.
    "about", "give", "me", "tell", "know", "please", "want", "need",
    "let", "show", "find", "help", "just", "like", "some", "any", "info",
    "information", "please", "thanks", "thank",
}


@dataclass
class RetrievedChunk:
    chunk: DocumentChunk
    vector_score: float
    bm25_score: float
    fused_score: float


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in _STOPWORDS] or words


def _searchable_chunk_text(chunk: DocumentChunk) -> str:
    """Include section titles in retrieval without duplicating them in stored text."""
    section = getattr(chunk, "section", None) or ""
    return f"{section}\n{chunk.content}" if section else chunk.content


def _bm25_rank(query: str, chunks: list[DocumentChunk]) -> dict[str, float]:
    if not chunks:
        return {}
    corpus = [_tokenize(_searchable_chunk_text(c)) for c in chunks]
    bm25 = BM25Okapi(corpus)
    scores = bm25.get_scores(_tokenize(query))
    nonnegative_scores = [
        max(0.0, float(s)) if math.isfinite(float(s)) else 0.0
        for s in scores
    ]
    max_score = max(nonnegative_scores, default=0.0)
    if max_score <= 0.0:
        return {c.id: 0.0 for c in chunks}
    return {
        c.id: min(1.0, score / max_score)
        for c, score in zip(chunks, nonnegative_scores)
    }


async def _vector_rank(query: str, chunks: list[DocumentChunk]) -> tuple[dict[str, float], str]:
    """Semantic search via ChromaDB, restricted to the candidate chunk set passed in."""
    if not chunks:
        return {}, "n/a"
    valid_ids = {c.id for c in chunks}
    (query_vec,), backend = await embed_texts([query], input_type="query")
    # over-fetch from Chroma since results may include chunks outside this candidate set
    try:
        raw = vector_store.query(
            query_vec,
            top_k=max(len(chunks), settings.top_k_retrieval * 3),
            backend=backend,
        )
    except _VECTOR_AVAILABILITY_ERRORS as error:
        logger.warning(
            "Chroma retrieval unavailable (%s); using BM25-only results",
            type(error).__name__,
        )
        return {}, f"{backend}_chroma_unavailable"
    scores = {cid: sim for cid, sim in raw if cid in valid_ids}
    return scores, backend


def _rrf_fuse(
    bm25_scores: dict[str, float], vector_scores: dict[str, float], k: int = 60,
    bm25_weight: float = 1.0, vector_weight: float = 1.0,
) -> dict[str, float]:
    """
    Reciprocal Rank Fusion: combine two ranked lists by rank position, not raw
    score. Weights let a caller trust one signal more than the other - used
    here to lean on BM25 when the vector signal comes from the weak local
    fallback embedding rather than the real NVIDIA embedding model.
    """
    def to_ranks(scores: dict[str, float]) -> dict[str, int]:
        ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
        return {chunk_id: rank for rank, (chunk_id, _) in enumerate(ordered, start=1)}

    bm25_ranks = to_ranks(bm25_scores)
    vector_ranks = to_ranks(vector_scores)
    all_ids = set(bm25_ranks) | set(vector_ranks)

    fused = {}
    for chunk_id in all_ids:
        rrf = 0.0
        if chunk_id in bm25_ranks:
            rrf += bm25_weight / (k + bm25_ranks[chunk_id])
        if chunk_id in vector_ranks:
            rrf += vector_weight / (k + vector_ranks[chunk_id])
        fused[chunk_id] = rrf

    max_fused = max(fused.values()) if fused else 1.0
    return {cid: (score / max_fused if max_fused else 0.0) for cid, score in fused.items()}


async def hybrid_retrieve(
    query: str, chunks: list[DocumentChunk], top_k: int | None = None
) -> tuple[list[RetrievedChunk], str]:
    """
    Retrieve the top-k chunks for a query using BM25 + ChromaDB vector search
    fused with RRF. Returns the ranked results plus the embedding backend used.
    """
    top_k = top_k or settings.top_k_retrieval
    if not chunks:
        return [], "n/a"

    bm25_scores = _bm25_rank(query, chunks)
    vector_scores, backend = await _vector_rank(query, chunks)
    # The local fallback embedding is a deterministic hash, not a real
    # semantic model - trust BM25 more heavily until NVIDIA_API_KEY is set.
    bm25_weight, vector_weight = (1.0, 1.0) if backend == "nvidia" else (2.5, 0.4)
    fused_scores = _rrf_fuse(bm25_scores, vector_scores, bm25_weight=bm25_weight, vector_weight=vector_weight)

    by_id = {c.id: c for c in chunks}
    ranked_ids = sorted(fused_scores, key=lambda cid: fused_scores[cid], reverse=True)[:top_k]

    results = [
        RetrievedChunk(
            chunk=by_id[cid],
            vector_score=vector_scores.get(cid, 0.0),
            bm25_score=bm25_scores.get(cid, 0.0),
            fused_score=fused_scores[cid],
        )
        for cid in ranked_ids
    ]
    return results, backend
