import asyncio

import httpx

from app.llm import gateway_client as gateway_module


class _MockResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.request = httpx.Request("POST", "https://example.com")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code} error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self._payload


class _MockAsyncClient:
    def __init__(self, *args, **kwargs):
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, headers=None, json=None):
        self.calls.append(url)
        if url.endswith("/chat/completions") and len(self.calls) == 1:
            return _MockResponse(404, {})
        return _MockResponse(200, {"choices": [{"message": {"content": "ok from v1"}}]})


def test_gateway_client_falls_back_to_v1_chat_completions(monkeypatch):
    gateway_module.settings.key_gateway_url = "https://example.com"
    gateway_module.settings.key_gateway_api_key = "test-key"
    gateway_module.settings.key_gateway_chat_model = "gpt-4o-mini"

    monkeypatch.setattr(gateway_module.httpx, "AsyncClient", lambda *args, **kwargs: _MockAsyncClient())

    result = asyncio.run(
        gateway_module.GatewayClient().chat_completion([{"role": "user", "content": "hi"}])
    )

    assert result == "ok from v1"
