"""Tests for BM25 stopword handling and RRF fusion - both areas where real
bugs were found and fixed during development."""
from types import SimpleNamespace

from app.rag.retriever import _bm25_rank, _tokenize, _rrf_fuse


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


def test_bm25_searches_section_titles_as_well_as_chunk_content():
    chunks = [
        SimpleNamespace(id="overview", section="Company Overview", content="Founded in 2016."),
        SimpleNamespace(id="security", section="IT Security", content="Company accounts require MFA."),
        SimpleNamespace(id="leave", section="Annual Leave", content="Employees receive paid leave."),
    ]

    scores = _bm25_rank("overview", chunks)

    assert scores["overview"] == 1.0
    assert scores["security"] == 0.0
