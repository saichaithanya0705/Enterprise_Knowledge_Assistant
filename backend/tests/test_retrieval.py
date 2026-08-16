"""Tests for BM25 stopword handling and RRF fusion - both areas where real
bugs were found and fixed during development."""
from app.rag.retriever import _tokenize, _rrf_fuse


def test_tokenize_strips_stopwords_and_punctuation():
    tokens = _tokenize("How do I reset my password?")
    assert "password" in tokens
    assert "reset" in tokens
    assert "how" not in tokens
    assert "my" not in tokens


def test_tokenize_falls_back_to_raw_words_if_all_stopwords():
    # a query that is ONLY stopwords should not tokenize to an empty list
    tokens = _tokenize("how do i")
    assert len(tokens) > 0


def test_rrf_prefers_top_bm25_when_weighted():
    bm25 = {"a": 1.0, "b": 0.0}
    vector = {"a": 0.1, "b": 0.9}  # vector signal disagrees
    fused = _rrf_fuse(bm25, vector, bm25_weight=2.5, vector_weight=0.4)
    assert fused["a"] > fused["b"]
