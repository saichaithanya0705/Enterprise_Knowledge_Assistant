"""
Thin HTTP client for NVIDIA NIM (build.nvidia.com / integrate.api.nvidia.com):
embeddings and reranking only - chat/answer generation goes through the Key
Gateway instead (see gateway_client.py). The API key comes only from the
NVIDIA_API_KEY environment variable and is never exposed to the frontend.
Retries transient failures with backoff.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings

settings = get_settings()

_RETRYABLE = (httpx.TransportError, httpx.HTTPStatusError)


class NvidiaApiError(Exception):
    pass


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
           retry=retry_if_exception_type(_RETRYABLE), reraise=True)
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
            data = resp.json()
            return [item["embedding"] for item in data["data"]]

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
           retry=retry_if_exception_type(_RETRYABLE), reraise=True)
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
            rankings = resp.json()["rankings"]
            scores_by_index = {r["index"]: r["logit"] for r in rankings}
            return [scores_by_index.get(i, 0.0) for i in range(len(passages))]


nvidia_client = NvidiaClient()
