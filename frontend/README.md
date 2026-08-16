# Enterprise Knowledge Assistant frontend

This is the React/Vite client for the Enterprise Knowledge Assistant. It provides the chat workspace, persisted conversation history, source excerpts, RAG trace inspection, document management, upload/chunk preview, provider status, and feedback controls.

## Local setup

```bash
npm install
copy .env.example .env
npm run dev
```

Set `VITE_API_URL` in `.env` when the FastAPI service is not running at `http://localhost:8000`.

## Verification commands

```bash
npm test
npm run lint
npm run build
```

The tests cover the user-visible contracts that are easy to regress: sibling document controls, keyboard-operable conversation/file controls, provider and index lifecycle status labels, stored debug traces, older trace shapes, chunk-preview failures, upload retry behavior, disabled suggestions/regenerate actions, and stale history/send responses after conversation changes.

## Current behavior

- Conversation history is request-identity checked, so a late response from a previous selection cannot replace the selected conversation.
- Creating, selecting, or deleting the active conversation clears the current message/debug view while the new history loads.
- Historical assistant messages use the API `debug` field to reopen their stored RAG trace.
- The trace separates BM25, vector, RRF-fused, and final-rerank scores. Missing fields in older traces are shown as `—`.
- Provider status consumes `chat_backend`, `embedding_backend`, and `rerank_backend`. Configured-but-unverified providers are displayed as `configured (unverified)`, never as live.
- Index lifecycle status preserves `index_status`, reingest/legacy-generation flags, and pending cleanup/action fields from `/api/system/status`; incomplete, degraded, empty, or unavailable coverage shows a non-live warning.
- `/api/system/status` is configuration and index lifecycle metadata, not persisted provider health. Completed request traces are the per-call evidence of the backend actually used.
- Document chunk preview failures are shown in the document row and surfaced through the toast stack.
- Upload failures remain in the dialog with an inline retry state; successful uploads close the dialog.

The backend must be running before chat or document actions can succeed. The frontend does not perform provider health checks; `/api/system/status` is a configuration/status signal and completed request traces are the source of truth for the backend actually used.
