# Architecture

## Layers

```
React (src/pages, src/components)
   → src/services (apiClient, documentService, chatService)
      → FastAPI routes (app/api/routes)
         → Pydantic validation (app/schemas)
            → Service layer (app/services) — orchestration only, no I/O logic itself
               → Repositories (app/repositories) — SQLite access
               → RAG pipeline (app/rag) — chunking, embeddings, retrieval, reranking, context
               → LLM client (app/llm) — NVIDIA NIM HTTP calls
```

Routes never touch the database or call NVIDIA directly — they validate input, call a service function, and shape the response. All ingestion and query orchestration lives in `app/services/*`, so it's testable and reusable outside the HTTP layer (e.g. from `seed.py`).

## Why ChromaDB is the vector source of truth

SQLite stores chunk text and metadata for joins and display (fast, relational, already needed for documents/conversations). Vectors are high-dimensional and only ever used for similarity search, so they live in ChromaDB instead of a JSON blob column — this is what "real" vector search looks like at small scale, and it means the retrieval code queries a purpose-built ANN index rather than looping over rows in Python.

Both stores are kept in sync at the service layer: `document_service.ingest_document` writes chunk rows to SQLite and chunk vectors to Chroma in the same request; `document_repo.delete_document` deletes from Chroma before the SQLite row (and its cascade-deleted chunks).

## Why every AI stage has a local fallback

The chat model runs through your Key Gateway and embeddings/reranking run through NVIDIA — two separate credentials that may arrive at different times. Rather than the app being unusable until both are set, every stage (query rewriting, embeddings, reranking, generation) checks its own provider's `configured` flag independently and falls back to a clearly-labeled non-AI substitute. This means:
- The full pipeline (ingest → chunk → retrieve → rerank → filter → answer) is testable and demoable today, with either, both, or neither credential set
- Nothing pretends to be AI-generated when it isn't — the debug panel and `/api/system/status` always report the real backend per stage
- Swapping in either credential later requires zero code changes, only setting the relevant env vars

## RRF weighting

Reciprocal Rank Fusion normally weights BM25 and vector search equally. When running on the local fallback (hash-based, not semantically meaningful) embedding, that would let noise from the vector leg outrank a strong BM25 match. `retriever.hybrid_retrieve` detects which embedding backend produced the vector scores and shifts the RRF weight toward BM25 (2.5:0.4) in fallback mode, back to equal (1:1) once NVIDIA embeddings are live. This was found and fixed during development by testing real queries against the seeded sample documents — see the retrieval tests in `tests/test_retrieval.py`.
