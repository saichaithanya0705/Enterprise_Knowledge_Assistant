# Scoped AI Slop Audit

**Audit date:** 2026-08-16  
**Scope:** Frontend files changed during the editorial Knowledge Desk redesign, their direct tests and service contracts, the backend chat/upload contracts they consume, and the relevant CI workflow.  
**Verdict:** Minimal residual slop risk after repair  
**Score:** 14 / 100  
**Confidence:** Medium

## Executive assessment

The redesign is visually cohesive and its main interaction architecture is maintainable, but the first implementation introduced four confirmed slop-like failures at trust boundaries: it could overstate grounding, advertised an upload policy without enforcing it before the network boundary, reported clipboard success when copying failed, and displayed a keyboard shortcut that did not exist. These were not treated as copy-only defects. The response model, upload boundary, clipboard state machine, and navigation affordance were corrected and backed by focused regression tests.

No broad repository-wide AI-slop claim is made. This audit is intentionally bounded to the code changed in this prompt plus directly connected frontend tests, backend schemas/routes/tests, package scripts, and CI.

## Evidence basis

- **Graph evidence:** graphify-out/GRAPH_REPORT.md does not exist. Per the audit workflow, the bundled Graphify triage scan was not applicable and was not run.
- **Source evidence:** Changed frontend components and tests were inspected directly, together with backend/app/schemas/chat.py, backend/app/api/routes/documents.py, backend/tests/test_documents_api.py, and .github/workflows/ci.yml.
- **Provenance:** The audited redesign was AI-assisted in this prompt. Findings are classified from artifact evidence, not presumed from authorship.
- **Validation evidence:** 28 frontend tests passed; frontend lint and production build passed; four backend document API tests passed; git diff --check -- frontend docs passed.

## Confirmed findings and permanent repairs

| Signal | Graph evidence | Source evidence | Classification | Root cause | Permanent fix | Prevention gate |
| --- | --- | --- | --- | --- | --- | --- |
| Every assistant answer was labeled “Grounded response” | Unavailable; no Graphify output | Backend explicitly models grounded: bool at backend/app/schemas/chat.py:49, and tests prove a valid response can be ungrounded at backend/tests/test_documents_api.py:30-34. The UI now retains the field at frontend/src/pages/ChatPage.jsx:50-58 and :114-118. | Confirmed trust-boundary defect | The redesign optimized the visual treatment around the happy path and discarded a meaningful backend state. | Preserve explicit grounding state, use source presence only as a compatibility fallback, and render either “Grounded response” or “No cited evidence” in frontend/src/components/MessageBubble.jsx:11-13,59. | frontend/src/pages/ChatPage.test.jsx:52-53 asserts a source-less answer cannot receive the grounded label. |
| Upload UI advertised PDF/DOCX/TXT/MD and 10 MB but sent invalid files to the backend | Unavailable; no Graphify output | Backend policy is authoritative at backend/app/api/routes/documents.py:17-18,31-35. The frontend now validates through frontend/src/components/documentUploadPolicy.js:1-15, invoked at frontend/src/components/UploadModal.jsx:61. | Confirmed contract-blind boundary | Policy text and behavior were duplicated informally without a frontend validation boundary. | Centralize the browser-side policy in one module and reject unsupported/oversize files before enabling upload; backend validation remains authoritative. | Negative tests at frontend/src/components/UploadModal.test.jsx:76-98 prove the upload callback is not invoked. |
| Copy action always announced success | Unavailable; no Graphify output | frontend/src/components/MessageBubble.jsx:18-25 now awaits the Clipboard API and distinguishes copied/failed states; frontend/src/components/MessageBubble.test.jsx:25 covers rejection. | Confirmed false-success state | An optional API call was treated as successful regardless of API availability or rejection. | Use an explicit asynchronous state machine with timer cleanup and a visible “Copy unavailable” outcome. | Clipboard rejection regression test. |
| New-conversation control displayed a nonfunctional Command-N hint | Unavailable; no Graphify output | The control now carries the decorative ledger index 01 at frontend/src/components/Sidebar.jsx:110; no shortcut claim remains. | Confirmed phantom affordance | Visual polish introduced behavior-signaling text without implementing or testing the behavior. | Remove the misleading shortcut and retain a non-interactive index consistent with the editorial navigation system. | UI review rule: keyboard hints require a registered handler and interaction test. |

## Architecture review

### Healthy signals

- The chat page guards against stale history and send responses with request identity refs rather than accepting whichever promise resolves last.
- The response contract is validated by backend schema and endpoint tests, and the UI no longer converts a probabilistic answer into a deterministic trust claim.
- Upload behavior has one browser-side policy module and still relies on server enforcement as the security boundary.
- The redesign introduced no new runtime dependencies, raw HTML injection, dynamic evaluation, or broad service abstraction.
- CI already runs backend tests and bytecode compilation plus frontend tests, lint, and production build at .github/workflows/ci.yml:25-26,41-43.

### Residual risks and unreviewed areas

- There is no Graphify artifact, so graph-level reachability, duplicate-structure, and dependency fan-out evidence was unavailable.
- The project uses JavaScript rather than a static typecheck gate; API response drift is therefore caught mainly by tests and runtime behavior.
- There is no automated accessibility scan or visual-regression suite. Responsive behavior was manually checked during the redesign, but those checks are not yet a CI gate.
- Upload constants exist in both Python and JavaScript because the browser cannot import the backend module. The server remains authoritative; generating a shared contract would be worthwhile if upload policy changes frequently.
- Unchanged backend retrieval, ingestion, and persistence internals were outside this prompt-scoped audit.

## Repair rationale

The repairs were made at the contract and state-management boundaries because changing labels alone would preserve the underlying false assumptions. A copy-only workaround, permissive upload attempt followed by server error, or unconditional grounded badge would be smaller edits but would keep behavior misleading and brittle. The chosen design makes uncertain model evidence explicit, validates before side effects, and keeps the backend as the final authority.

Other valid patterns include generating frontend policy constants from an OpenAPI schema, adding a real Command-N handler with focus-aware keyboard tests, and replacing the local clipboard state machine with a tested shared action hook if additional copy surfaces appear. Those add machinery that is not justified by the current number of consumers.

## Validation

| Check | Result |
| --- | --- |
| npm test -- --run | Passed: 9 files, 28 tests |
| npm run lint | Passed |
| npm run build | Passed: 1,814 modules transformed |
| python -m pytest tests/test_documents_api.py -q | Passed: 4 tests; one unrelated OpenTelemetry deprecation warning |
| git diff --check -- frontend docs | Passed; Git only reported informational LF-to-CRLF conversion warnings |

## Completion decision

The confirmed AI-slop signals introduced or exposed by this redesign are fixed for the scoped edits. In accordance with the completion gate, the AI-slop check was not rerun after the repairs and this report update.
