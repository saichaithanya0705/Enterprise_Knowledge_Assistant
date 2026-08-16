"""Regression tests for typed AI contracts, fallbacks, and trace semantics."""
from types import SimpleNamespace

import httpx
import pytest

from app.llm import gateway_client as gateway_module
from app.llm import nvidia_client as nvidia_module
from app.llm import llm_service as llm_service_module
from app.llm.llm_service import generate_answer
from app.prompts import templates as templates_module
from app.prompts.templates import NO_CONTEXT_FALLBACK, SYSTEM_INSTRUCTIONS
from app.rag import context_builder as context_module
from app.rag import embeddings as embeddings_module
from app.rag import query_improver as query_module
from app.rag import retriever as retriever_module
from app.rag.context_builder import ContextChunk
from app.rag.retriever import RetrievedChunk
from app.schemas.chat import RetrievedChunkTrace
from app.services import chat_service


class _Response:
    def __init__(self, payload):
        self.status_code = 200
        self._payload = payload
        self.request = httpx.Request("POST", "https://example.com")

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _StatusResponse(_Response):
    def __init__(self, status_code, payload=None):
        super().__init__(payload or {})
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"{self.status_code} error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )


class _PayloadClient:
    def __init__(self, payload):
        self.payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _Response(self.payload)


class _SequenceClient:
    def __init__(self, outcomes, state):
        self.outcomes = outcomes
        self.state = state

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        outcome = self.outcomes[min(self.state["calls"], len(self.outcomes) - 1)]
        self.state["calls"] += 1
        if isinstance(outcome, Exception):
            raise outcome
        status_code, payload = outcome
        return _StatusResponse(status_code, payload)


def _configure_gateway(monkeypatch):
    monkeypatch.setattr(gateway_module.settings, "key_gateway_url", "https://example.com")
    monkeypatch.setattr(gateway_module.settings, "key_gateway_api_key", "test-key")


def _configure_nvidia(monkeypatch):
    monkeypatch.setattr(nvidia_module.settings, "nvidia_api_key", "test-key")


@pytest.mark.asyncio
async def test_query_rewrite_falls_back_for_transport_and_invalid_rewrites(monkeypatch):
    _configure_gateway(monkeypatch)
    fallback = query_module._rule_based_expand("How do I use PTO?")

    async def raise_transport(*args, **kwargs):
        raise httpx.ConnectError("gateway unavailable")

    monkeypatch.setattr(query_module.gateway_client, "chat_completion", raise_transport)
    assert await query_module.improve_query("How do I use PTO?") == fallback

    request = httpx.Request("POST", "https://example.com")
    response = httpx.Response(429, request=request)

    async def raise_http_error(*args, **kwargs):
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr(query_module.gateway_client, "chat_completion", raise_http_error)
    assert await query_module.improve_query("How do I use PTO?") == fallback

    for malformed in (None, ["not a query"], "x" * 10_001):
        async def return_malformed(*args, value=malformed, **kwargs):
            return value

        monkeypatch.setattr(query_module.gateway_client, "chat_completion", return_malformed)
        assert await query_module.improve_query("How do I use PTO?") == fallback


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"choices": []},
        {"choices": [{}]},
        {"choices": [{"message": {}}]},
        {"choices": [{"message": {"content": None}}]},
    ],
)
async def test_gateway_200_payload_shape_errors_are_gateway_errors(monkeypatch, payload):
    _configure_gateway(monkeypatch)
    monkeypatch.setattr(gateway_module.httpx, "AsyncClient", lambda *args, **kwargs: _PayloadClient(payload))

    with pytest.raises(gateway_module.GatewayError):
        await gateway_module.GatewayClient().chat_completion([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
@pytest.mark.parametrize("transient_status", [429, 503])
async def test_gateway_retries_transient_status_then_succeeds(monkeypatch, transient_status):
    _configure_gateway(monkeypatch)
    state = {"calls": 0}
    outcomes = [
        (transient_status, {}),
        (200, {"choices": [{"message": {"content": "ok after retry"}}]}),
    ]
    monkeypatch.setattr(
        gateway_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient(outcomes, state),
    )

    result = await gateway_module.GatewayClient().chat_completion([{"role": "user", "content": "hi"}])

    assert result == "ok after retry"
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_gateway_retries_unlisted_5xx_then_succeeds(monkeypatch):
    _configure_gateway(monkeypatch)
    state = {"calls": 0}
    outcomes = [
        (507, {}),
        (200, {"choices": [{"message": {"content": "ok after retry"}}]}),
    ]
    monkeypatch.setattr(
        gateway_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient(outcomes, state),
    )

    result = await gateway_module.GatewayClient().chat_completion([{"role": "user", "content": "hi"}])

    assert result == "ok after retry"
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_gateway_retries_transport_failure_then_succeeds(monkeypatch):
    _configure_gateway(monkeypatch)
    state = {"calls": 0}
    outcomes = [
        httpx.ConnectError("temporary network failure"),
        (200, {"choices": [{"message": {"content": "ok after retry"}}]}),
    ]
    monkeypatch.setattr(
        gateway_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient(outcomes, state),
    )

    result = await gateway_module.GatewayClient().chat_completion([{"role": "user", "content": "hi"}])

    assert result == "ok after retry"
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_gateway_permanent_401_is_typed_without_retries(monkeypatch):
    _configure_gateway(monkeypatch)
    state = {"calls": 0}
    outcomes = [(401, {})]
    monkeypatch.setattr(
        gateway_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient(outcomes, state),
    )

    with pytest.raises(gateway_module.GatewayError):
        await gateway_module.GatewayClient().chat_completion([{"role": "user", "content": "hi"}])

    assert state["calls"] == 1


@pytest.mark.asyncio
async def test_empty_context_refuses_without_calling_live_gateway(monkeypatch):
    _configure_gateway(monkeypatch)
    calls = []

    async def unexpected_call(*args, **kwargs):
        calls.append((args, kwargs))
        raise AssertionError("empty context must not call the live gateway")

    monkeypatch.setattr(gateway_module.gateway_client, "chat_completion", unexpected_call)

    answer, backend = await generate_answer("", "What is the leave policy?")

    assert answer == NO_CONTEXT_FALLBACK
    assert backend == "local_fallback"
    assert calls == []


@pytest.mark.asyncio
async def test_uncited_live_answer_uses_extractively_grounded_local_fallback(monkeypatch):
    _configure_gateway(monkeypatch)

    async def uncited_answer(*args, **kwargs):
        return "Employees receive the answer from somewhere else."

    monkeypatch.setattr(gateway_module.gateway_client, "chat_completion", uncited_answer)
    context = "[1] leave-policy.txt\nEmployees receive 18 days of annual leave."

    answer, backend = await generate_answer(context, "How much leave do employees receive?")

    assert backend == "local_fallback"
    assert "Employees receive 18 days of annual leave." in answer


def test_prompt_preview_redacts_history_and_is_bounded():
    preview_builder = getattr(templates_module, "build_prompt_preview", None)
    assert callable(preview_builder)
    context = "Current context: PTO is approved by a manager.\n\nQuestion: this text belongs to the context."
    question = "Actual current question: How do I request PTO?"
    messages = templates_module.build_chat_messages(
        context,
        question,
        history=[{"role": "user", "content": "Old confidential question"}],
    )

    preview = preview_builder(messages, context=context, question=question)
    assert "user question: Actual current question: How do I request PTO?" in preview
    assert "user question: this text belongs to the context." not in preview
    long_preview = preview_builder(
        templates_module.build_chat_messages("x" * 10_000, "Current question"),
        context="x" * 10_000,
        question="Current question",
    )

    assert "Old confidential question" not in preview
    assert "prior conversation message" in preview
    assert "Current context: PTO is approved by a manager." in preview
    assert "Question: this text belongs to the context." in preview
    assert len(long_preview) <= 2_000


@pytest.mark.asyncio
async def test_generate_answer_passes_prepared_messages_to_gateway_without_rebuilding(monkeypatch):
    _configure_gateway(monkeypatch)
    prepared_messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user", "content": "Context:\n[1] policy.txt\nPTO is approved.\n\nQuestion: How?"},
    ]
    captured = {}

    async def capture_messages(messages, **kwargs):
        captured["messages"] = messages
        return "PTO is approved [1]"

    monkeypatch.setattr(llm_service_module.gateway_client, "chat_completion", capture_messages)

    answer, backend = await generate_answer(
        "[1] policy.txt\nPTO is approved.",
        "How?",
        prepared_messages=prepared_messages,
    )

    assert answer == "PTO is approved [1]"
    assert backend == "key_gateway"
    assert captured["messages"] is prepared_messages


@pytest.mark.asyncio
async def test_rerank_handles_extreme_finite_logits_without_overflow(monkeypatch):
    _configure_nvidia(monkeypatch)

    async def extreme_logits(*args, **kwargs):
        return [-1000.0, 1000.0]

    monkeypatch.setattr(context_module.nvidia_client, "rerank", extreme_logits)
    retrieved = [
        RetrievedChunk(SimpleNamespace(content="first"), 0.1, 0.2, 0.3),
        RetrievedChunk(SimpleNamespace(content="second"), 0.4, 0.5, 0.6),
    ]

    reranked, backend = await context_module.rerank("first second", retrieved)

    assert backend == "nvidia"
    assert reranked[0].rerank_score > 0.999
    assert reranked[1].rerank_score < 0.001


@pytest.mark.asyncio
@pytest.mark.parametrize("transient_status", [429, 507])
async def test_nvidia_retries_transient_statuses(monkeypatch, transient_status):
    _configure_nvidia(monkeypatch)
    state = {"calls": 0}
    outcomes = [
        (transient_status, {}),
        (200, {"data": [{"index": 0, "embedding": [1.0, 2.0]}]}),
    ]
    monkeypatch.setattr(
        nvidia_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient(outcomes, state),
    )

    vectors = await nvidia_module.NvidiaClient().embed(["leave policy"])

    assert vectors == [[1.0, 2.0]]
    assert state["calls"] == 2


@pytest.mark.asyncio
async def test_nvidia_retries_transport_failures(monkeypatch):
    _configure_nvidia(monkeypatch)
    state = {"calls": 0}
    outcomes = [
        httpx.ConnectError("temporary network failure"),
        (200, {"data": [{"index": 0, "embedding": [1.0, 2.0]}]}),
    ]
    monkeypatch.setattr(
        nvidia_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient(outcomes, state),
    )

    vectors = await nvidia_module.NvidiaClient().embed(["leave policy"])

    assert vectors == [[1.0, 2.0]]
    assert state["calls"] == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [401, 403, 404])
async def test_nvidia_permanent_http_errors_fail_fast_into_local_fallback(monkeypatch, status_code):
    _configure_nvidia(monkeypatch)
    state = {"calls": 0}
    monkeypatch.setattr(
        nvidia_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _SequenceClient([(status_code, {})], state),
    )

    vectors, backend = await embeddings_module.embed_texts(["leave policy"])

    assert backend == "local_fallback"
    assert len(vectors) == 1
    assert state["calls"] == 1


@pytest.mark.asyncio
async def test_malformed_nvidia_payloads_raise_typed_errors(monkeypatch):
    _configure_nvidia(monkeypatch)
    monkeypatch.setattr(nvidia_module.httpx, "AsyncClient", lambda *args, **kwargs: _PayloadClient({"data": [{}]}))
    with pytest.raises(nvidia_module.NvidiaApiError):
        await nvidia_module.NvidiaClient().embed(["leave policy"])

    monkeypatch.setattr(
        nvidia_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _PayloadClient({"rankings": [{}]}),
    )
    with pytest.raises(nvidia_module.NvidiaApiError):
        await nvidia_module.NvidiaClient().rerank("leave policy", ["18 days leave"])


@pytest.mark.asyncio
async def test_nvidia_embeddings_reorder_by_index_and_validate_vectors(monkeypatch):
    _configure_nvidia(monkeypatch)
    payload = {
        "data": [
            {"index": 1, "embedding": [2.0, 3.0]},
            {"index": 0, "embedding": [1.0, 2.0]},
        ]
    }
    monkeypatch.setattr(nvidia_module.httpx, "AsyncClient", lambda *args, **kwargs: _PayloadClient(payload))

    vectors = await nvidia_module.NvidiaClient().embed(["first", "second"])

    assert vectors == [[1.0, 2.0], [2.0, 3.0]]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        {"data": [{"embedding": [1.0]}, {"index": 1, "embedding": [2.0]}]},
        {"data": [{"index": 0, "embedding": [1.0]}, {"index": 0, "embedding": [2.0]}]},
        {"data": [{"index": 0, "embedding": [1.0]}, {"index": 2, "embedding": [2.0]}]},
        {"data": [{"index": 0, "embedding": []}, {"index": 1, "embedding": [2.0]}]},
        {"data": [{"index": 0, "embedding": [1.0]}, {"index": 1, "embedding": [2.0, 3.0]}]},
    ],
)
async def test_nvidia_embeddings_reject_malformed_index_or_vector_contract(monkeypatch, payload):
    _configure_nvidia(monkeypatch)
    monkeypatch.setattr(nvidia_module.httpx, "AsyncClient", lambda *args, **kwargs: _PayloadClient(payload))

    with pytest.raises(nvidia_module.NvidiaApiError):
        await nvidia_module.NvidiaClient().embed(["first", "second"])


@pytest.mark.asyncio
async def test_malformed_nvidia_errors_trigger_local_embedding_and_rerank_fallbacks(monkeypatch):
    _configure_nvidia(monkeypatch)
    monkeypatch.setattr(
        nvidia_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _PayloadClient({"data": [{}]}),
    )
    vectors, embedding_backend = await embeddings_module.embed_texts(["leave policy"])
    assert embedding_backend == "local_fallback"
    assert len(vectors) == 1

    monkeypatch.setattr(
        nvidia_module.httpx,
        "AsyncClient",
        lambda *args, **kwargs: _PayloadClient({"rankings": [{}]}),
    )
    chunk = SimpleNamespace(content="leave policy and annual leave")
    retrieved = [RetrievedChunk(chunk=chunk, vector_score=0.2, bm25_score=0.5, fused_score=1.0)]
    reranked, rerank_backend = await context_module.rerank("leave policy", retrieved)
    assert rerank_backend == "local_fallback"
    assert reranked[0].retrieved is retrieved[0]


def test_bm25_trace_scores_are_nonnegative_and_bounded(monkeypatch):
    class _FakeBm25:
        def __init__(self, corpus):
            self.corpus = corpus

        def get_scores(self, query):
            return [-3.0, 7.0]

    monkeypatch.setattr(retriever_module, "BM25Okapi", _FakeBm25)
    chunks = [
        SimpleNamespace(id="first", content="leave policy"),
        SimpleNamespace(id="second", content="annual leave"),
    ]

    scores = retriever_module._bm25_rank("leave", chunks)

    assert scores == {"first": 0.0, "second": 1.0}
    assert all(0.0 <= score <= 1.0 for score in scores.values())


def test_trace_schema_exposes_distinct_rerank_score():
    trace = RetrievedChunkTrace(
        chunk_id="chunk-1",
        filename="policy.txt",
        vector_score=0.1,
        bm25_score=0.2,
        fused_score=0.3,
        rerank_score=0.9,
        used_in_context=True,
        excerpt="policy excerpt",
    )

    assert trace.fused_score == 0.3
    assert trace.rerank_score == 0.9


@pytest.mark.asyncio
async def test_chat_trace_preserves_context_order_and_complete_prompt(monkeypatch):
    document = SimpleNamespace(filename="policy.txt")
    first_chunk = SimpleNamespace(id="first", document_id="doc", document=document, section=None, content="First policy")
    second_chunk = SimpleNamespace(id="second", document_id="doc", document=document, section=None, content="Second policy")
    first = ContextChunk(
        retrieved=RetrievedChunk(first_chunk, vector_score=0.1, bm25_score=0.2, fused_score=0.3),
        rerank_score=0.9,
    )
    second = ContextChunk(
        retrieved=RetrievedChunk(second_chunk, vector_score=0.4, bm25_score=0.5, fused_score=0.6),
        rerank_score=0.8,
    )
    conversation = SimpleNamespace(id="conversation", messages=[SimpleNamespace(role="user", content="Earlier question")])
    assistant_message = SimpleNamespace(id="assistant-message")

    monkeypatch.setattr(chat_service.conversation_repo, "get_or_create_conversation", lambda *args, **kwargs: conversation)
    monkeypatch.setattr(chat_service.conversation_repo, "add_message", lambda *args, **kwargs: assistant_message)
    monkeypatch.setattr(chat_service.document_repo, "list_ready_chunks", lambda db: [first_chunk, second_chunk])

    async def improve(query):
        return query

    async def retrieve(query, chunks):
        return [first.retrieved, second.retrieved], "local_fallback"

    async def build(query, retrieved):
        return [first, second], [first, second], "local_fallback"

    monkeypatch.setattr(chat_service, "improve_query", improve)
    monkeypatch.setattr(chat_service, "hybrid_retrieve", retrieve)
    monkeypatch.setattr(chat_service, "build_context", build)
    monkeypatch.setattr(chat_service, "format_context_for_prompt", lambda used: "[1] policy.txt\nFirst policy\n\n---\n\n[2] policy.txt\nSecond policy")

    async def answer(context, question, history, prepared_messages):
        assert prepared_messages
        return "Grounded answer [1]", "key_gateway"

    monkeypatch.setattr(chat_service, "generate_answer", answer)

    _, _, _, sources, debug, grounded = await chat_service.answer_question(None, None, "What is the policy?")

    assert grounded is True
    assert [source["chunk_id"] for source in sources] == ["first", "second"]
    assert debug["retrieved_chunks"][0]["fused_score"] == 0.3
    assert debug["retrieved_chunks"][0]["rerank_score"] == 0.9
    assert debug["final_context_chunk_ids"] == ["first", "second"]
    assert "system: You are the Enterprise Knowledge Assistant" in debug["prompt_preview"]
    assert "Earlier question" not in debug["prompt_preview"]
    assert "prior conversation message" in debug["prompt_preview"]
    assert "What is the policy?" in debug["prompt_preview"]
    assert "First policy" in debug["prompt_preview"]
    assert len(debug["prompt_preview"]) <= 2_000
