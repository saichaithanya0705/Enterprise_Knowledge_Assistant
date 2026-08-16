# Submission Readiness Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every P1/P2 issue from the README compliance audit and add regression coverage for provider failures, persisted traces, API validation, accurate debug data, and frontend interaction semantics.

**Architecture:** Preserve the existing FastAPI service/repository and React service/component boundaries. Provider clients validate external response contracts and convert malformed output into typed errors; orchestration catches those typed or transport errors before side effects and falls back transparently. API schemas enforce documented values, conversation history exposes the stored trace, and the frontend consumes the corrected trace contract with semantic controls.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, pytest, httpx, React 19, Vite, Vitest, Testing Library, Tailwind CSS.

---

### Task 1: Provider resilience, grounding validation, and accurate retrieval traces

**Files:**
- Create: `backend/tests/test_ai_resilience.py`
- Modify: `backend/app/rag/query_improver.py`
- Modify: `backend/app/rag/retriever.py`
- Modify: `backend/app/llm/gateway_client.py`
- Modify: `backend/app/llm/nvidia_client.py`
- Modify: `backend/app/llm/llm_service.py`
- Modify: `backend/app/prompts/templates.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/services/chat_service.py`

- [ ] **Step 1: Write failing provider-contract and fallback tests**

```python
@pytest.mark.asyncio
async def test_query_improver_falls_back_on_transport_error(monkeypatch):
    monkeypatch.setattr(gateway_client, "configured", True)
    monkeypatch.setattr(gateway_client, "chat_completion", AsyncMock(side_effect=httpx.TransportError("offline")))
    assert await improve_query("PTO policy") == "paid time off policy"

@pytest.mark.asyncio
async def test_answer_without_valid_citation_uses_extractive_fallback(monkeypatch):
    monkeypatch.setattr(gateway_client, "configured", True)
    monkeypatch.setattr(gateway_client, "chat_completion", AsyncMock(return_value="Unsupported answer"))
    answer, backend = await generate_answer("[1] leave.txt\n18 days", "How much leave?")
    assert backend == "local_fallback"
    assert "[1] leave.txt" in answer

def test_gateway_rejects_malformed_success_payload():
    # A 200 response without choices[0].message.content must raise GatewayError.
    ...
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && python -m pytest tests/test_ai_resilience.py -v`

Expected: failures showing transport errors escape, malformed output is accepted or raises an untyped exception, and citationless answers are returned.

- [ ] **Step 3: Implement typed provider validation and transparent fallback**

```python
def _validated_chat_content(payload: object) -> str:
    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise GatewayError("Key Gateway returned an invalid response shape") from exc
    if not isinstance(content, str) or not content.strip():
        raise GatewayError("Key Gateway returned empty content")
    return content.strip()

def _has_valid_context_citation(answer: str, context: str) -> bool:
    source_count = sum(1 for line in context.splitlines() if re.match(r"^\[\d+\] ", line))
    return any(f"[{index}]" in answer for index in range(1, source_count + 1))
```

Catch `GatewayError` and `httpx.HTTPError` in query improvement; reject non-string/oversized rewrites; skip live generation when context is empty; validate citations before persisting a live answer; validate NVIDIA embedding/rerank payload shape, cardinality, finite numeric values, and indexes before returning them.

- [ ] **Step 4: Separate BM25, RRF fusion, and rerank scores in the trace**

```python
class RetrievedChunkTrace(BaseModel):
    chunk_id: str
    filename: str
    section: str | None = None
    vector_score: float
    bm25_score: float
    fused_score: float
    rerank_score: float
    used_in_context: bool
    excerpt: str
```

Clamp normalized BM25 scores to `0..1`, preserve final context ID order, and build `prompt_preview` from the same message list passed to generation rather than from context alone. The preview must be bounded and omit prior conversation contents while still showing the system role, current context, and current question; this keeps the trace useful without persisting every historical message twice.

- [ ] **Step 5: Run focused and full backend tests**

Run: `cd backend && python -m pytest tests/test_ai_resilience.py tests/test_retrieval.py tests/test_documents_api.py -v`

Expected: all focused tests pass.

Run: `cd backend && python -m pytest tests/ -v`

Expected: all backend tests pass.

### Task 2: Embedding-index lifecycle, atomic ingestion, and truthful provider status

**Files:**
- Create: `backend/tests/test_index_lifecycle.py`
- Modify: `backend/app/rag/embeddings.py`
- Modify: `backend/app/rag/vector_store.py`
- Modify: `backend/app/rag/retriever.py`
- Modify: `backend/app/services/document_service.py`
- Modify: `backend/app/repositories/document_repo.py`
- Modify: `backend/app/api/routes/system.py`

- [ ] **Step 1: Write failing lifecycle and compensation tests**

```python
@pytest.mark.asyncio
async def test_local_and_nvidia_vectors_use_dimension_safe_collections(...):
    # Index a 256-d local vector, then a mocked 1024-d NVIDIA vector.
    # Both upserts and backend-specific queries must succeed without dimension errors.
    ...

@pytest.mark.asyncio
async def test_failed_vector_upsert_leaves_no_chunk_rows(client, monkeypatch):
    monkeypatch.setattr(vector_store, "upsert_chunks", Mock(side_effect=RuntimeError("index failed")))
    response = client.post("/api/documents", files={"file": ("x.txt", io.BytesIO(b"POLICY\nbody"), "text/plain")})
    assert response.status_code == 422
    failed = client.get("/api/documents").json()[0]
    assert failed["status"] == "failed"
    assert client.get(f"/api/documents/{failed['id']}/chunks").json() == []
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && python -m pytest tests/test_index_lifecycle.py -v`

Expected: Chroma rejects the backend dimension switch and failed ingestion leaves committed chunk rows.

- [ ] **Step 3: Implement backend-specific vector collections and compensating persistence**

```python
def collection_name(backend: str) -> str:
    if backend not in {"local_fallback", "nvidia"}:
        raise ValueError(f"Unsupported embedding backend: {backend}")
    return f"document_chunks_{backend}"
```

Pass the actual embedding backend into vector upsert/query, isolate incompatible dimensions by collection, and delete a document/chunk from every owned collection. Flush chunk rows without committing before vector upsert; commit only after indexing succeeds; on any later failure roll back SQLite and compensate by deleting possibly-partial vector IDs before marking the document failed.

- [ ] **Step 4: Stop reporting configured providers as live**

Return explicit configuration states (`local_fallback` or `configured_unverified`) from `/api/system/status`; retain the existing booleans for compatibility. Frontend/docs must label configuration truthfully unless runtime health has actually been observed.

- [ ] **Step 5: Run focused and full backend tests**

Run: `cd backend && python -m pytest tests/test_index_lifecycle.py tests/test_documents_api.py -v`

Expected: focused tests pass.

Run: `cd backend && python -m pytest tests/ -v`

Expected: all backend tests pass.

### Task 3: Conversation trace persistence and strict API contracts

**Files:**
- Create: `backend/tests/test_api_contracts.py`
- Modify: `backend/app/db/database.py`
- Modify: `backend/app/schemas/document.py`
- Modify: `backend/app/schemas/chat.py`
- Modify: `backend/app/schemas/feedback.py`
- Modify: `backend/app/api/routes/documents.py`
- Modify: `backend/app/api/routes/conversations.py`
- Modify: `backend/app/api/routes/feedback.py`
- Modify: `backend/app/api/routes/chat.py`
- Modify: `backend/app/repositories/conversation_repo.py`
- Modify: `backend/app/models/conversation.py`
- Modify: `backend/app/services/chat_service.py`

- [ ] **Step 1: Write failing API regression tests**

```python
def test_persisted_assistant_message_returns_debug_trace(client):
    # Upload, chat, reload messages, then require messages[-1]["debug"].
    assert messages[-1]["debug"]["original_query"] == "How do I reset my password?"

@pytest.mark.parametrize("rating", [0, 2, -2])
def test_feedback_rejects_non_thumb_rating(client, rating):
    assert client.post("/api/feedback", json={"message_id": "x", "rating": rating}).status_code == 422

def test_feedback_rejects_unknown_message(client):
    assert client.post("/api/feedback", json={"message_id": str(uuid.uuid4()), "rating": 1}).status_code == 404

def test_deleting_conversation_cascades_feedback(client):
    # Create a conversation, assistant message and feedback, delete the conversation,
    # then assert no Feedback row remains.
    ...

def test_document_upload_rejects_unknown_category(client):
    response = client.post("/api/documents", files={"file": ("x.txt", io.BytesIO(b"text"), "text/plain")}, data={"category": "Payroll"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd backend && python -m pytest tests/test_api_contracts.py -v`

Expected: trace field is absent and invalid feedback/category requests are accepted.

- [ ] **Step 3: Implement schema and repository validation**

```python
DocumentCategory = Literal["HR", "IT", "Finance", "General"]

class FeedbackRequest(BaseModel):
    message_id: str
    rating: Literal[-1, 1]
    comment: str | None = Field(default=None, max_length=1000)

class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[dict] | None = None
    debug: DebugTrace | None = None
    created_at: str
```

Validate category at the FastAPI boundary, look up feedback targets and allow only assistant messages, return 404 for an unknown conversation ID instead of silently creating another conversation, and enable SQLite foreign-key enforcement on each connection.

- [ ] **Step 4: Run focused and full backend tests**

Run: `cd backend && python -m pytest tests/test_api_contracts.py tests/test_documents_api.py -v`

Expected: all focused tests pass.

Run: `cd backend && python -m pytest tests/ -v`

Expected: all backend tests pass.

### Task 4: Frontend semantics, race safety, trace presentation, accessibility, and documentation

**Files:**
- Create: `frontend/src/pages/DocumentsPage.test.jsx`
- Create: `frontend/src/components/DebugPanel.test.jsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/src/pages/DocumentsPage.jsx`
- Modify: `frontend/src/pages/ChatPage.jsx`
- Modify: `frontend/src/components/DebugPanel.jsx`
- Modify: `frontend/src/components/MessageBubble.jsx`
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/components/UploadModal.jsx`
- Modify: `frontend/src/components/ChatInput.jsx`
- Modify: `frontend/src/components/Toast.jsx`
- Modify: `frontend/README.md`
- Modify: `README.md`
- Modify: `docs/feature-list.md`
- Modify: `docs/architecture.md`
- Modify: `docs/presentation-flow.md`

- [ ] **Step 1: Add Vitest/Testing Library and write failing UI tests**

```jsx
it("renders document expand and delete as sibling buttons", async () => {
  render(<DocumentsPage />);
  expect(await screen.findByRole("button", { name: /show chunks for/i })).toBeVisible();
  expect(screen.getByRole("button", { name: /delete/i }).closest("button button")).toBeNull();
});

it("shows separate RRF and rerank scores", () => {
  render(<DebugPanel debug={trace} onClose={() => {}} />);
  expect(screen.getByText("RRF")).toBeVisible();
  expect(screen.getByText("Rerank")).toBeVisible();
});

it("ignores stale conversation history responses", async () => {
  // Resolve conversation B, then resolve an older request for A.
  // The rendered messages must still belong to B.
});
```

- [ ] **Step 2: Run UI tests and verify RED**

Run: `cd frontend && npm test -- --run`

Expected: tests fail because Vitest configuration/semantic labels/separate score rendering are missing.

- [ ] **Step 3: Implement semantic controls and accurate trace UI**

Make expand and delete sibling buttons, add accessible names to icon-only controls, catch chunk-preview load errors, disable suggestion buttons while sending, render BM25/Vector/RRF/Rerank separately, and preserve historical trace buttons through the corrected API response. Guard conversation-history and in-flight send results with request identity/cancellation so stale responses cannot overwrite the active conversation, and reset any open trace when the active conversation changes.

- [ ] **Step 4: Update documentation to current behavior**

Document `NVIDIA_RERANK_URL=https://integrate.api.nvidia.com/v1/ranking`, instruct users to copy `.env.example` instead of claiming `.env` ships, remove the stale numeric test count, explain provider response validation/fallback behavior, and replace the template frontend README with project-specific instructions.

- [ ] **Step 5: Run frontend tests, lint, and build**

Run: `cd frontend && npm test -- --run`

Expected: all UI tests pass.

Run: `cd frontend && npm run lint && npm run build`

Expected: lint exits without errors and Vite production build succeeds.

### Task 5: Integrated verification and independent review

**Files:**
- Review all files changed by Tasks 1-3.

- [ ] **Step 1: Run full validation**

```powershell
Set-Location backend
python -m pytest tests/ -v
python -m compileall -q app seed.py
Set-Location ..\frontend
npm test -- --run
npm run lint
npm run build
```

- [ ] **Step 2: Re-run original black-box regressions**

Verify configured-provider transport/malformed output returns a grounded local fallback rather than HTTP 500; persisted messages include `debug`; invalid ratings, message IDs, and categories are rejected; debug scores and prompt preview match their labels.

- [ ] **Step 3: Independent spec and code-quality review**

Review every README audit finding against the final diff, then review maintainability, error boundaries, API compatibility, accessibility, and test quality. Resolve every Critical/Important issue before completion.
