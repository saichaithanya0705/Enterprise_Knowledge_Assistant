# Feature List

## Mandatory (from project brief)
- [x] Document ingestion: PDF, DOCX, TXT
- [x] Configurable chunk size + overlap
- [x] Vector store integration (ChromaDB) for similarity search
- [x] Prompt template forcing the LLM to answer only from retrieved context
- [x] Source citation shown alongside every answer
- [x] Chat-style interface for asking questions

## Additional features
- [x] MD file support alongside PDF/DOCX/TXT
- [x] Structure-aware chunking (splits on headings before falling back to sliding window)
- [x] Hybrid retrieval: BM25 + vector search fused with weighted RRF
- [x] Second-stage cross-encoder reranking (NVIDIA nv-rerankqa)
- [x] Query improvement/rewriting before retrieval
- [x] Context deduplication + relevance thresholding
- [x] Full RAG debug/trace view (query → BM25/vector/RRF/final-rerank scores → context → bounded prompt preview → backend)
- [x] Multi-turn conversation memory, persisted per conversation
- [x] Thumbs up/down feedback per answer
- [x] Document manager with per-chunk preview
- [x] Category tagging (HR / IT / Finance / General)
- [x] Transparent local-fallback mode for every AI stage — fully demoable with zero API keys
- [x] Automated tests for chunking, retrieval fusion, API contracts, and frontend race/accessibility behavior
- [x] JWT registration/login with database-backed USER/ADMIN authorization
- [x] Owner-scoped conversations and feedback; foreign resource IDs return 404 without creating replacements
- [x] Soft deletion, user restore requests, admin approval/rejection, and admin-only permanent deletion
- [x] Admin control room for users, documents, conversations, persisted RAG traces, audit logs, and real analytics
- [x] Profile/password management and environment-driven bootstrap-admin provisioning

## Index lifecycle

- [x] Backend-specific Chroma collections keep local fallback and NVIDIA vector dimensions separate
- [x] Legacy vector data is preserved for compatibility and deletion cleanup
- [x] Existing documents require semantic reingestion after a model/dimension generation change; backend index status/action signals and the frontend warning identify incomplete coverage before relying on semantic retrieval
