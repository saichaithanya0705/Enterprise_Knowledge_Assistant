# Architecture

## Layers

```
React (public auth, protected user workspace, admin control room)
   → token-aware src/services API boundary
      → FastAPI routes (app/api/routes)
         → JWT identity dependency + database-backed role/ownership checks
         → Pydantic validation (app/schemas)
            → Service layer (app/services) — orchestration only, no I/O logic itself
               → Repositories (app/repositories) — SQLite access
               → RAG pipeline (app/rag) — chunking, embeddings, retrieval, reranking, context
               → LLM clients (app/llm) — Key Gateway chat and NVIDIA embedding/rerank HTTP calls
```

Routes validate input and shape responses. They may call a service or repository for the operation at hand; longer ingestion and query orchestration lives in `app/services/*`, so it remains testable and reusable outside the HTTP layer (e.g. from `seed.py`). Provider calls stay behind `app/llm/*` and RAG operations behind `app/rag/*`.

Authentication is enforced server-side: Bearer tokens provide only a user id, while current role and active status are reloaded from SQLite on every protected request. Conversation and feedback repositories scope normal-user access by that database identity; only admin dependencies can cross ownership boundaries, inspect raw excerpts/debug traces, manage documents, or resolve recovery requests.

Existing pre-authentication SQLite databases are upgraded idempotently with nullable ownership and soft-delete columns. Legacy conversations remain preserved as unowned records visible to administrators; fresh databases receive the complete ORM foreign-key constraints.

## Why ChromaDB is the vector source of truth

SQLite stores chunk text and metadata for joins and display (fast, relational, already needed for documents/conversations). Vectors are high-dimensional and only ever used for similarity search, so they live in ChromaDB instead of a JSON blob column — this is what "real" vector search looks like at small scale, and it means the retrieval code queries a purpose-built ANN index rather than looping over rows in Python.

Both stores are coordinated at the service layer: `document_service.ingest_document` flushes chunk rows, writes vectors, and commits the document only after indexing succeeds; failures roll back SQLite, attempt to compensate vector writes, and mark the document failed. `document_repo.delete_document` removes vectors from current backend collections and the preserved legacy collection before deleting the SQLite row and its cascade-deleted chunks.

## Vector index generations

Chroma collections are separated by embedding backend, model, and dimension, so the fixed 256-dimensional local fallback cannot be mixed with an NVIDIA vector of a different dimension. A configured model or dimension change is a new index generation and requires semantic reingestion before the new generation can be treated as complete. Legacy vectors remain preserved for compatibility and cleanup, but new retrieval uses the selected current generation; backend index status/action fields and the frontend warning make reingestion visible to operators.

## Why every AI stage has a local fallback

The chat model runs through your Key Gateway and embeddings/reranking run through NVIDIA — two separate credentials that may arrive at different times. Rather than the app being unusable until both are set, every stage (query rewriting, embeddings, reranking, generation) checks its own provider's `configured` flag independently and falls back to a clearly-labeled non-AI substitute. This means:
- The full pipeline (ingest → chunk → retrieve → rerank → filter → answer) is testable and demoable today, with either, both, or neither credential set
- Nothing pretends to be AI-generated when it isn't — request traces report the backend used per stage, while `/api/system/status` remains configuration-only and reports configured providers as `configured_unverified`; it does not persist live health
- Swapping in either credential later requires zero code changes, only setting the relevant env vars

## RRF weighting

Reciprocal Rank Fusion normally weights BM25 and vector search equally. When running on the local fallback (hash-based, not semantically meaningful) embedding, `retriever.hybrid_retrieve` shifts the RRF weight toward BM25 (2.5:0.4); NVIDIA embeddings use equal (1:1) weighting. The debug panel displays raw BM25/vector scores, the RRF fused score, and the final reranker score as separate stages.
