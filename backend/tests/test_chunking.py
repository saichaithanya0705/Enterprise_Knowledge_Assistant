"""Unit tests for the chunking strategy."""
from app.rag.chunking import chunk_document, clean_text


def test_short_section_stays_one_chunk():
    text = "POLICY TITLE\nThis is a short paragraph under the heading."
    chunks = chunk_document(text, chunk_size=800, chunk_overlap=100)
    assert len(chunks) == 1
    assert chunks[0].section == "POLICY TITLE"


def test_long_section_splits_with_overlap():
    body = "This is a sentence about company policy. " * 50
    text = f"LONG POLICY\n{body}"
    chunks = chunk_document(text, chunk_size=300, chunk_overlap=50)
    assert len(chunks) > 1
    # every chunk should carry the section title through
    assert all(c.section == "LONG POLICY" for c in chunks)


def test_clean_text_collapses_whitespace():
    messy = "Line one\r\n\r\n\r\nLine   two"
    cleaned = clean_text(messy)
    assert "\r" not in cleaned
    assert "\n\n\n" not in cleaned
