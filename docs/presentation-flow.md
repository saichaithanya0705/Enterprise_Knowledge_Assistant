# Presentation / Demo Flow

1. **Problem** — employees waste time searching scattered HR/IT/Finance docs for simple answers.
2. **Solution** — upload once, ask in chat, get a cited grounded answer.
3. **Show `/api/system/status`** — explain local-fallback vs. NVIDIA-live mode, and that the app runs honestly either way.
4. **Upload a document live** — Documents page, drag-and-drop, watch it go processing → ready, expand to see its chunks.
5. **Ask a grounded question** — e.g. "How do I reset my password?" — show the cited answer and expand a source card to see the excerpt.
6. **Open the debug trace** — walk through: original query → improved query → every retrieved candidate with BM25/vector/rerank scores → which chunks made the final context → the actual prompt sent → which backend answered.
7. **Ask an off-topic question** — show it declines rather than inventing an answer.
8. **Explain the architecture** — layered backend, BM25+vector+RRF fusion, NVIDIA reranking, ChromaDB as the vector store.
9. **Explain the local-fallback design decision** — why every AI stage degrades transparently instead of the app being unusable pre-credentials.
10. **Future improvements** — streaming responses, caching, role-based document access.
