"""Unit tests for the chunking strategy."""
from app.rag.chunking import chunk_document, clean_text
from app.rag.loaders import _clean_pdf_pages


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


def test_pdf_table_labels_do_not_fragment_values_into_tiny_chunks():
    text = """6. Equipment Stipend for Remote Work
Allowance
Amount
Frequency
Home office setup
$750
One-time, first 60 days
Internet / connectivity stipend
$50/month
Monthly, added to payroll"""

    chunks = chunk_document(text, chunk_size=800, chunk_overlap=100)

    assert len(chunks) == 1
    assert "$750" in chunks[0].content
    assert "$50/month" in chunks[0].content


def test_pdf_cleanup_removes_repeated_page_furniture_but_keeps_body_text():
    pages = [
        f"Employee Handbook\nConfidential - Internal\nPage {number}\nUnique policy body {number}"
        for number in range(1, 5)
    ]

    cleaned = _clean_pdf_pages(pages)

    assert "Employee Handbook" not in cleaned
    assert "Confidential - Internal" not in cleaned
    assert "Page 1" not in cleaned
    assert "Unique policy body 1" in cleaned
