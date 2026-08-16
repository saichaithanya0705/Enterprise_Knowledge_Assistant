"""
Thin HTTP client for the Key Gateway - used only for chat/answer generation
(and query rewriting). OpenAI-compatible chat completions endpoints commonly
use either /chat/completions or /v1/chat/completions depending on provider.
Credentials come only from environment variables and are never exposed to the
frontend. Retries transient failures with backoff.
"""
import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.llm.openai_compat import ChatCompletionContractError, extract_chat_content

settings = get_settings()

class GatewayError(Exception):
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

    async def chat_completion(self, messages: list[dict], temperature: float = 0.2) -> str:
        if not self.configured:
            raise GatewayError("Key Gateway is not configured")

        try:
            return await self._chat_completion_with_retries(messages, temperature)
        except GatewayError:
            raise
        except httpx.HTTPError as exc:
            raise GatewayError(f"Key Gateway request failed after retries: {exc}") from exc

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
           retry=retry_if_exception(_is_retryable), reraise=True)
    async def _chat_completion_with_retries(self, messages: list[dict], temperature: float) -> str:
        return await self._chat_completion_attempt(messages, temperature)

    async def _chat_completion_attempt(self, messages: list[dict], temperature: float) -> str:
        last_error: Exception | None = None
        async with httpx.AsyncClient(timeout=30) as client:
            for url in self._candidate_urls():
                try:
                    resp = await client.post(
                        url,
                        headers=self._headers(),
                        json={"model": settings.key_gateway_chat_model, "messages": messages, "temperature": temperature},
                    )
                    resp.raise_for_status()
                    try:
                        payload = resp.json()
                    except (TypeError, ValueError) as exc:
                        raise GatewayError("Key Gateway returned invalid JSON") from exc
                    try:
                        return extract_chat_content(payload, "Key Gateway")
                    except ChatCompletionContractError as exc:
                        raise GatewayError(str(exc)) from exc
                except httpx.HTTPStatusError as exc:
                    if exc.response is not None and exc.response.status_code in {404, 405}:
                        last_error = exc
                        continue
                    raise

        if last_error is not None:
            raise GatewayError(f"Key Gateway request failed: {last_error}")
        raise GatewayError("Key Gateway request failed without a response")


gateway_client = GatewayClient()
