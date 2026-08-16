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
- [x] Full RAG debug/trace view (query → scores → context → prompt → backend)
- [x] Multi-turn conversation memory, persisted per conversation
- [x] Thumbs up/down feedback per answer
- [x] Document manager with per-chunk preview
- [x] Category tagging (HR / IT / Finance / General)
- [x] Transparent local-fallback mode for every AI stage — fully demoable with zero API keys
- [x] Automated tests for chunking, retrieval fusion, and the API (10 tests)
