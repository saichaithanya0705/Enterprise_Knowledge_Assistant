"""
Thin HTTP client for the Key Gateway - used only for chat/answer generation
(and query rewriting). OpenAI-compatible chat completions endpoints commonly
use either /chat/completions or /v1/chat/completions depending on provider.
Credentials come only from environment variables and are never exposed to the
frontend. Retries transient failures with backoff.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import get_settings

settings = get_settings()

_RETRYABLE = (httpx.TransportError, httpx.HTTPStatusError)


class GatewayError(Exception):
    pass


class GatewayClient:
    def __init__(self):
        self.base_url = settings.key_gateway_url.rstrip("/") if settings.key_gateway_url else ""
        self.api_key = settings.key_gateway_api_key

    @property
    def configured(self) -> bool:
        return settings.key_gateway_configured

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def _candidate_urls(self) -> list[str]:
        if not self.base_url:
            return []

        urls = [self.base_url]
        if not self.base_url.endswith("/v1"):
            urls.append(f"{self.base_url}/v1")

        candidates: list[str] = []
        for base in urls:
            candidates.append(f"{base}/chat/completions")
            if not base.endswith("/v1"):
                candidates.append(f"{base}/v1/chat/completions")
        # Deduplicate while preserving preference order.
        seen: set[str] = set()
        ordered: list[str] = []
        for candidate in candidates:
            if candidate not in seen:
                seen.add(candidate)
                ordered.append(candidate)
        return ordered

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
           retry=retry_if_exception_type(_RETRYABLE), reraise=True)
    async def chat_completion(self, messages: list[dict], temperature: float = 0.2) -> str:
        if not self.configured:
            raise GatewayError("Key Gateway is not configured")

        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=30) as client:
            for url in self._candidate_urls():
                try:
                    resp = await client.post(
                        url,
                        headers=self._headers(),
                        json={"model": settings.key_gateway_chat_model, "messages": messages, "temperature": temperature},
                    )
                    if resp.status_code == 404:
                        last_error = httpx.HTTPStatusError(
                            f"404 Client Error: Not Found for url: {url}",
                            request=resp.request,
                            response=resp,
                        )
                        continue
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
                except httpx.HTTPStatusError as exc:
                    last_error = exc
                    if exc.response is not None and exc.response.status_code in {404, 405}:
                        continue
                    # Any other HTTP error (401/403/429/5xx) must surface as
                    # GatewayError, not a raw httpx exception - the caller
                    # (llm_service.generate_answer) only catches GatewayError
                    # to trigger its extractive fallback; a bare re-raise here
                    # skips that fallback and crashes the whole chat request.
                    raise GatewayError(f"Key Gateway request failed: {exc}") from exc

        if last_error is not None:
            raise GatewayError(f"Key Gateway request failed: {last_error}")
        raise GatewayError("Key Gateway request failed without a response")


gateway_client = GatewayClient()