"""
Embedding service. Responsible only for turning text into vectors - never
for generating answers (that's the LLM service's job) and never for scoring
relevance (that's the reranker's job).

Uses NVIDIA's NV-Embed model (asymmetric query/passage embeddings) when
NVIDIA_API_KEY is configured. Falls back to a deterministic local hashing
vector so the retrieval pipeline is fully demoable before a real key is
added. Every response reports which backend produced it.
"""
import hashlib
import logging
import math

import httpx

from app.llm.nvidia_client import nvidia_client, NvidiaApiError

logger = logging.getLogger(__name__)

LOCAL_EMBEDDING_DIM = 256


def _local_embed_one(text: str) -> list[float]:
    """
    Deterministic, dependency-free fallback embedding: hashes words into a
    fixed-size vector and L2-normalizes. Not semantically strong, but stable
    and good enough to demo the full pipeline without a live NVIDIA key.
    """
    vec = [0.0] * LOCAL_EMBEDDING_DIM
    for w in text.lower().split():
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        idx = h % LOCAL_EMBEDDING_DIM
        sign = 1.0 if (h // LOCAL_EMBEDDING_DIM) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


async def embed_texts(texts: list[str], input_type: str = "passage") -> tuple[list[list[float]], str]:
    """Returns (vectors, backend_name). input_type: 'passage' when indexing, 'query' when searching."""
    if nvidia_client.configured:
        try:
            vectors = await nvidia_client.embed(texts, input_type=input_type)
            return vectors, "nvidia"
        except (NvidiaApiError, httpx.HTTPError) as e:
            # Same class of bug as the reranker: an HTTP-level failure
            # (bad/expired key, quota, retired endpoint, network) must not
            # take down document ingestion or retrieval - fall back to the
            # local embedding instead.
            logger.warning("NVIDIA embed failed, falling back to local embedding: %s", e)
    return [_local_embed_one(t) for t in texts], "local_fallback"


def cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
    norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (norm_a * norm_b)