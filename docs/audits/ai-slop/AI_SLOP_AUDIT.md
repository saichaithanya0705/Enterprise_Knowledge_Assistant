# Scoped AI Slop Audit

**Audit date:** 2026-08-17

**Scope:** The NVIDIA chat fallback, OpenAI-compatible response validation, Render bootstrap administrator, provider status reporting, deployment configuration, and their directly connected tests and CI gates.

**Verdict:** Minimal residual slop risk after repair

**Score:** 17 / 100

**Confidence:** Medium

## Executive assessment

The deployment slice is now behaviorally sound and was independently exercised against the live Render services. Three confirmed slop-like defects were found and repaired: the first bootstrap implementation treated an existing administrator as proof that the configured credential was current; the extractive fallback could make a false claim about provider configuration; and configuration comments contradicted the newly added NVIDIA chat role. The fixes restore one authoritative environment-to-database bootstrap boundary, keep fallback copy provider-neutral, and align operational documentation with source.

No repository-wide authorship claim is made. The audited changes were AI-assisted in this task, but classifications below are based on verified artifacts and runtime behavior rather than style or presumed provenance.

## Evidence basis

- **Graph evidence:** `graphify-out/GRAPH_REPORT.md` does not exist. The bundled Graphify triage scanner was therefore not applicable and was not run.
- **Source evidence:** Commits `27d7c17`, `4f9ab23`, and `9336401` were inspected with their provider, bootstrap, repository, status, deployment, and test contracts.
- **Runtime evidence:** The live Render deployment authenticated the configured administrator, ingested a synthetic PDF into two chunks, returned `ORBIT-7429 [1]`, expanded the cited source, and identified NVIDIA chat and NVIDIA embeddings in the trace.
- **External limitation:** `https://keygateway1.arshnivlabs.com` timed out before TLS during the deployment work. It was not configured because doing so would add repeated request delays; the NVIDIA chat fallback was used and verified instead.

## Evidence

| Signal | Graph evidence | Source or runtime evidence | Classification | Root cause | Permanent fix | Prevention gate |
| --- | --- | --- | --- | --- | --- | --- |
| Bootstrap administrator ignored rotated environment credentials once the email existed | Unavailable | Live login remained `401` after rotating the Render secret; the old implementation returned the existing row without reconciling it. The repaired transaction is at `backend/app/repositories/user_repo.py:42`, called from `backend/app/services/admin_bootstrap.py:31-39`. | Confirmed slop signal | Creation-only happy-path logic treated identity existence as configuration convergence. | Synchronize name, password when changed, `ADMIN` role, and active state in one repository transaction while preserving the user id. | `backend/tests/test_bootstrap_admin.py:40` proves password rotation, role restoration, activation, name synchronization, and stable identity. Live API login returned `200` with role `ADMIN`. |
| Local fallback claimed the Key Gateway was not configured even when a configured gateway had failed | Unavailable | The fallback text encoded provider state in `backend/app/llm/llm_service.py`; the new neutral contract is at line 25. | Confirmed slop signal | A fallback presentation string was coupled to only one route into the fallback. | Describe the deterministic behavior, not a guessed failure cause: provider generation unavailable, extractive answer used. | `backend/tests/test_ai_resilience.py:263` configures a gateway, forces failure, and rejects the false `not configured` claim. |
| NVIDIA configuration comments still said embeddings and reranking only | Unavailable | The provider chain uses NVIDIA chat, while `backend/app/core/config.py` and `backend/.env.example` retained the old role description. | Confirmed documentation mismatch | Operational documentation was not updated with the provider responsibility change. | Update both source and environment-template comments to include chat fallback. | Review gate: provider-role changes must update config comments, example environment, status contract, and tests together. |
| Provider output could be malformed or uncited | Unavailable | `backend/app/llm/openai_compat.py:8` validates the OpenAI-compatible payload; `backend/app/llm/llm_service.py:31,59,68` rejects answers without an in-range citation. | Healthy architecture signal | N/A | Shared deterministic response validation and citation gating remain at the provider boundary. | Malformed-payload, retry, fail-fast, uncited-answer, and failover tests in `backend/tests/test_ai_resilience.py`. |
| Configured services could be mistaken for verified services | Unavailable | `backend/app/api/routes/system.py:23-27` reports `configured_unverified`, not `healthy`. The live trace separately recorded actual backends used for the answer. | Healthy architecture signal | N/A | Preserve the distinction between static configuration and per-request execution evidence. | Status tests assert the explicit state; browser E2E inspected the request trace. |

## Highest-risk cluster

The provider-selection and bootstrap-startup paths are the highest-risk connected cluster because they cross environment secrets, external networks, persistent identity, and user-visible trust claims. The repaired design keeps provider response validation in one module, provider order in one service, persistence in one repository transaction, and startup orchestration in one bootstrap service. No new factory, registry, dynamic loader, or speculative abstraction was introduced.

## Healthy signals

- Provider responses are validated before persistence, and generated answers must cite a source id that exists in the supplied context.
- Transient NVIDIA failures retry; permanent authentication or contract failures fail into explicit fallback behavior.
- The bootstrap password is sourced only from process environment and is hashed before persistence.
- The Render JWT secret is generated externally, CORS is restricted to the deployed frontend, and API keys are `sync: false` secrets rather than committed values.
- CI runs backend tests and compilation plus frontend tests, lint, and production build at `.github/workflows/ci.yml:25,41-43`.
- Regression tests are semantic: they verify wrong-password rejection, password rotation, identity stability, role/active restoration, payload validation, retry counts, failover order, and citation enforcement rather than snapshots or truthiness.

## Workflow gaps and residual risk

- Graph-level cohesion and reachability could not be assessed because no Graphify artifact exists; confidence remains Medium.
- CI has no dependency vulnerability scan, secret scan, SAST, or browser E2E gate. These are workflow gaps, not proof of a current vulnerability.
- Live provider health cannot be inferred from `configured_unverified`; operators must use a controlled provider probe or request trace.
- The NVIDIA reranker was configured during the browser test but the request trace recorded `local_fallback`; retrieval still succeeded through hybrid search, and NVIDIA chat/embeddings were proven. The provider-specific rerank failure reason is not surfaced in the UI.
- Render free-tier SQLite, uploaded files, and Chroma storage are ephemeral and can be lost after restart or redeploy. This deployment is suitable for the stated presentation, not durable production.

## Likely root causes

- **Happy-path trust:** the initial bootstrap assumed `user exists` meant `configured credential is current`.
- **Context-specific wording:** the local fallback message described one historical cause rather than the behavior guaranteed by the fallback contract.
- **Review artifact drift:** provider responsibilities changed faster than adjacent configuration comments.
- **Missing external gates:** live provider and browser flows are manual because CI has no credential-bound staging checks.

## Permanent fixes completed

1. Added one atomic repository operation to synchronize the configured bootstrap administrator.
2. Added a regression test that proves rotation and identity/authorization convergence.
3. Replaced provider-assumption fallback copy with a provider-neutral deterministic contract.
4. Added a regression test for the configured-but-unavailable gateway path.
5. Updated NVIDIA role documentation in source and the environment template.

## Anti-slop gates recommended

- Add dependency, secret, and static-security scans to CI without using force-upgrade automation.
- Add a credential-injected staging E2E job that uploads a synthetic PDF and asserts answer text, citation, source expansion, and trace backend.
- Record a bounded, secret-free last provider failure classification so operators can distinguish authentication, endpoint, rate-limit, timeout, and malformed-response fallbacks.
- Generate or refresh Graphify output before the next repository-wide architecture audit.

## Validation

| Check | Result |
| --- | --- |
| Focused RED test for provider-neutral fallback | Failed before repair with the old `no Key Gateway configured` text |
| Focused post-repair tests | Passed: 4 tests |
| Full backend test suite | Passed: 121 tests; one external OpenTelemetry deprecation warning |
| Previous frontend validation for the deployed revision | Passed: 31 tests, lint, and Vite production build |
| Live admin auth | Passed: HTTP 200, JWT issued, role `ADMIN` |
| Live PDF upload/index | Passed: 1 PDF, 2 ready chunks |
| Live grounded chat | Passed: correct `ORBIT-7429 [1]` answer with expandable source |
| Live provider trace | NVIDIA embeddings and NVIDIA chat; ChromaDB vector store; local rerank fallback |

## Completion decision

The confirmed slop-like signals in this deployment slice are fixed. In accordance with the completion gate, the AI-slop scan was not rerun after repair; only behavior validation was run.
