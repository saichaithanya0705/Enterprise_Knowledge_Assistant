# Evidence-First AI-Slop Audit

**Audit date:** 2026-08-16

**Audited change:** `d5dc819` (`fix: harden submission readiness across RAG stack`) plus the directly connected persistence, RAG/provider, frontend state, dependency, and verification boundaries.

**Purpose:** identify slop-like engineering risk and review debt. This report does not infer whether any code was authored by a person or a model.

## Verdict

**Post-repair risk score: 11/100 (low), confidence 0.88.** No unresolved P1 or P2 defect was confirmed in the audited slice. Four confirmed maintainability/verification issues were repaired: a test-only production persistence path, a suppressed React dependency contract, an unbounded ChromaDB dependency, and tests that inherited live local credentials. A missing CI gate was also corrected.

Graphify evidence was unavailable because `graphify-out/GRAPH_REPORT.md` does not exist. Per the audit procedure, the Graphify triage scanner was therefore not run; source, call-site, diff, test, dependency, and repository-governance evidence were used instead. Confidence is below 1.0 because no graph was available and the newly added CI workflow has not yet run on a remote GitHub runner.

## Evidence table

| Severity | Status | Evidence | Assessment |
|---|---|---|---|
| P2 | Fixed | `backend/app/repositories/conversation_repo.py` had an `add_turn(db=None, ...)` branch described as supporting a unit test. It called an otherwise unused `add_message`, which immediately dereferenced `db` and could not be a valid runtime path. The sole test mock of `add_message` was in `backend/tests/test_ai_resilience.py`. | Test accommodation had leaked into production persistence and left dead indirection. The branch and wrapper were removed; the test now mocks the real `add_turn` persistence boundary. Real transaction behavior remains covered by `backend/tests/test_api_contracts.py`, including failed generation and concurrent turns. |
| P2 | Fixed | `frontend/src/pages/DocumentsPage.jsx` disabled `react-hooks/exhaustive-deps` for a loader that captured changing values. `frontend/src/context/ToastContext.jsx` also created a new provider object on every render. | Static feedback was suppressed instead of satisfying the lifecycle contract. The context value is memoized, the loader is a stable `useCallback`, the effect declares its dependency, and a regression assertion proves one initial list request. |
| P2 | Fixed | `backend/requirements.txt` pinned all direct dependencies except `chromadb>=1.0.0`; the validated environment uses ChromaDB 1.5.9. | The open-ended range allowed future incompatible major versions into the core index boundary. It is now pinned to `chromadb==1.5.9`. |
| P2 | Fixed | A full backend run with the configured local `.env` produced 4 failures and attempted NVIDIA calls because application settings are imported during test collection, before the per-test fixture can alter the environment. | `backend/tests/conftest.py` now forces provider credentials off before application imports. Provider tests opt in explicitly, so the default suite is deterministic, offline, and independent of developer secrets. |
| P2 | Fixed | The README documented backend tests and frontend test/lint/build commands, but `.github/workflows` did not exist. | A minimal read-only CI workflow now enforces backend tests/compilation and frontend tests/lint/build on pushes and pull requests. |
| Healthy | Verified | `backend/app/llm/gateway_client.py`, `backend/app/llm/nvidia_client.py`, and `backend/app/llm/llm_service.py` validate response shape, cardinality, numeric values, indexes, and in-range citations before results reach persistence. | Model/provider output is treated as probabilistic and untrusted; malformed or ungrounded output falls back through typed boundaries. |
| Healthy | Verified | `backend/app/services/document_service.py`, `backend/app/repositories/document_repo.py`, and `backend/app/rag/vector_store.py` use bounded retries, durable cleanup tasks, idempotent operations, and explicit degraded lifecycle status. Failure/race behavior is covered in `backend/tests/test_index_lifecycle.py`. | The cross-store SQLite/Chroma lifecycle has negative-path and recovery behavior rather than happy-path-only cleanup. |
| Healthy | Verified | `backend/.env` and `frontend/.env` are ignored, only `.env.example` files are tracked, and the provided credential is not in Git. | No committed secret was found in the audited repository state. |

## Scorecard

| Category | Risk |
|---|---:|
| Structural health and graph erosion | 3/20 |
| Maintainability and idiomatic fit | 1/20 |
| Verification, test, and review integrity | 2/20 |
| Security, dependency, and agent hygiene | 2/15 |
| Workflow and governance controls | 2/15 |
| Documentation and provenance honesty | 1/10 |
| **Total** | **11/100** |

The non-zero structural score reflects a broad 59-file remediation and three large, domain-focused regression files, not a confirmed god object. `backend/app/rag/vector_store.py` (359 lines) is a future extraction candidate if it grows, but current functions remain grouped around one index-generation lifecycle. The tests are large (552, 600, and 712 lines), yet inspected assertions cover malformed provider output, persistence rollback, concurrency, cleanup races, and API semantics rather than snapshots or call-count-only mock theater.

## Root causes and permanent fixes

- **Test convenience crossing a runtime boundary:** injection was achieved by weakening a repository contract. The test now replaces the explicit persistence operation, leaving production types and behavior honest.
- **Lifecycle ownership left implicit:** the document loader depended on context/state while its effect hid that dependency. Stable context identity and a callback-based loader make ownership explicit.
- **Verification existed only as instructions:** repeatable commands were documented but not enforced. CI now runs the same checks from clean installs.
- **Dependency policy inconsistency:** one core data dependency used an open-ended lower bound. The validated version is now reproducible.
- **Credential-coupled tests:** settings were imported before fixtures could isolate them, allowing a local `.env` to change tests and trigger network calls. Credentials are now disabled before test-module collection, while provider tests opt in explicitly.

## Remaining review targets, not confirmed defects

- `frontend/src/App.jsx` and `frontend/src/components/Sidebar.jsx` accept several status aliases. This is currently bounded compatibility with the API's nested and top-level status fields, but the aliases should be removed if the API contract is versioned and older shapes are no longer supported.
- The in-process per-conversation lock in `backend/app/services/chat_service.py` is correct for the documented single-process local deployment. A multi-worker deployment would require a database/distributed serialization mechanism; that is a deployment-scope requirement, not a defect in the submitted local architecture.
- The workflow does not yet include Python lint/type checking, SAST, or a Python dependency vulnerability scanner. These are worthwhile hardening gates, but no existing project configuration currently defines their policies.

## Validation

- Focused backend AI resilience suite: **33 passed**, with one third-party OpenTelemetry deprecation warning.
- Focused document-page frontend suite: **5 passed**.
- Full backend suite: **100 passed**, with the same third-party OpenTelemetry deprecation warning.
- Python bytecode compilation: **passed**.
- Full frontend suite: **25 passed**.
- Frontend lint and production build: **passed**.
- Production dependency audit: **0 npm vulnerabilities**.
- CI workflow YAML structure and whitespace/error checks: **passed**.

Per the completion gate, the AI-slop scanner/audit was not rerun after these repairs.
