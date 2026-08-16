"""
Thin HTTP client for NVIDIA NIM (build.nvidia.com / integrate.api.nvidia.com):
embeddings and reranking only - chat/answer generation goes through the Key
Gateway instead (see gateway_client.py). The API key comes only from the
NVIDIA_API_KEY environment variable and is never exposed to the frontend.
Retries transient failures with backoff.
"""
import math

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings

settings = get_settings()

class NvidiaApiError(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        if response is None:
            return False
        return response.status_code == 429 or 500 <= response.status_code < 600
    return False


def _as_finite_float(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise NvidiaApiError(f"NVIDIA response contained an invalid {field}")
    return float(value)


class NvidiaClient:
    def __init__(self):
        self.base_url = settings.nvidia_base_url.rstrip("/")
        self.rerank_url = settings.nvidia_rerank_url
        self.api_key = settings.nvidia_api_key

    @property
    def configured(self) -> bool:
        return settings.nvidia_configured

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
           retry=retry_if_exception(_is_retryable), reraise=True)
    async def embed(self, texts: list[str], input_type: str = "passage") -> list[list[float]]:
        """input_type is 'query' for the user's question, 'passage' for indexed chunks -
        NVIDIA's NV-Embed models use asymmetric query/passage embeddings."""
        if not self.configured:
            raise NvidiaApiError("NVIDIA_API_KEY is not configured")
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={
                    "model": settings.nvidia_embedding_model,
                    "input": texts,
                    "input_type": input_type,
                    "encoding_format": "float",
                },
            )
            resp.raise_for_status()
            try:
                data = resp.json()
            except (TypeError, ValueError) as exc:
                raise NvidiaApiError("NVIDIA embeddings response was not valid JSON") from exc
            if not isinstance(data, dict) or not isinstance(data.get("data"), list):
                raise NvidiaApiError("NVIDIA embeddings response did not contain data")
            if len(data["data"]) != len(texts):
                raise NvidiaApiError("NVIDIA embeddings response count did not match input count")
            vectors_by_index = {}
            dimension = None
            for item in data["data"]:
                if not isinstance(item, dict) or not isinstance(item.get("embedding"), list):
                    raise NvidiaApiError("NVIDIA embeddings response contained an invalid embedding")
                index = item.get("index")
                if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(texts):
                    raise NvidiaApiError("NVIDIA embeddings response contained an invalid index")
                if index in vectors_by_index:
                    raise NvidiaApiError("NVIDIA embeddings response contained a duplicate index")
                embedding = item["embedding"]
                if not embedding:
                    raise NvidiaApiError("NVIDIA embeddings response contained an empty embedding")
                if dimension is None:
                    dimension = len(embedding)
                elif len(embedding) != dimension:
                    raise NvidiaApiError("NVIDIA embeddings response dimensions were inconsistent")
                vectors_by_index[index] = [
                    _as_finite_float(value, "embedding value") for value in embedding
                ]
            if set(vectors_by_index) != set(range(len(texts))):
                raise NvidiaApiError("NVIDIA embeddings response indexes were incomplete")
            return [vectors_by_index[index] for index in range(len(texts))]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
           retry=retry_if_exception(_is_retryable), reraise=True)
    async def rerank(self, query: str, passages: list[str]) -> list[float]:
        """Returns a relevance score per passage, in the same order as `passages`."""
        if not self.configured:
            raise NvidiaApiError("NVIDIA_API_KEY is not configured")
        if not passages:
            return []
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.rerank_url,
                headers=self._headers(),
                json={
                    "model": settings.nvidia_rerank_model,
                    "query": {"text": query},
                    "passages": [{"text": p} for p in passages],
                },
            )
            resp.raise_for_status()
            try:
                payload = resp.json()
            except (TypeError, ValueError) as exc:
                raise NvidiaApiError("NVIDIA rerank response was not valid JSON") from exc
            if not isinstance(payload, dict) or not isinstance(payload.get("rankings"), list):
                raise NvidiaApiError("NVIDIA rerank response did not contain rankings")
            rankings = payload["rankings"]
            scores_by_index = {}
            for ranking in rankings:
                if not isinstance(ranking, dict):
                    raise NvidiaApiError("NVIDIA rerank response contained an invalid ranking")
                index = ranking.get("index")
                if isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(passages):
                    raise NvidiaApiError("NVIDIA rerank response contained an invalid index")
                if index in scores_by_index:
                    raise NvidiaApiError("NVIDIA rerank response contained a duplicate index")
                scores_by_index[index] = _as_finite_float(ranking.get("logit"), "rerank score")
            if len(scores_by_index) != len(passages):
                raise NvidiaApiError("NVIDIA rerank response did not score every passage")
            return [scores_by_index.get(i, 0.0) for i in range(len(passages))]


nvidia_client = NvidiaClient()
