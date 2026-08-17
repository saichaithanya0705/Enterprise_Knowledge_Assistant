"""Document loaders: extract raw text from PDF, DOCX, and TXT/MD files."""
from collections import Counter
import io
import math
import re

from pypdf import PdfReader
import docx


class UnsupportedFileType(Exception):
    pass


def load_text(filename: str, raw_bytes: bytes) -> str:
    """Route to the right extractor based on file extension."""
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _load_pdf(raw_bytes)
    if lower.endswith(".docx"):
        return _load_docx(raw_bytes)
    if lower.endswith((".txt", ".md")):
        return raw_bytes.decode("utf-8", errors="ignore")
    raise UnsupportedFileType(f"Unsupported file type: {filename}")


def _load_pdf(raw_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return _clean_pdf_pages(pages)


_PAGE_NUMBER_RE = re.compile(r"^page\s+\d+(?:\s+of\s+\d+)?$", re.IGNORECASE)


def _clean_pdf_pages(pages: list[str]) -> str:
    """Remove repeated short headers/footers before documents are chunked.

    PDF extractors do not distinguish page furniture from policy text. Leaving
    a repeated company name, handbook title, and confidentiality footer on
    every page creates many tiny pseudo-sections and pollutes retrieval. A line
    is removed only when it appears on at least half of a 3+ page document;
    page-number-only lines are always removed.
    """
    page_lines = [page.splitlines() for page in pages]
    occurrences: Counter[str] = Counter()
    for lines in page_lines:
        occurrences.update(
            {
                normalized
                for line in lines
                if 3 <= len(normalized := " ".join(line.split()).casefold()) <= 120
            }
        )

    repeated: set[str] = set()
    if len(page_lines) >= 3:
        minimum_pages = max(3, math.ceil(len(page_lines) / 2))
        repeated = {line for line, count in occurrences.items() if count >= minimum_pages}

    cleaned_pages = []
    for lines in page_lines:
        kept = []
        for line in lines:
            normalized = " ".join(line.split())
            if not normalized:
                kept.append("")
                continue
            if _PAGE_NUMBER_RE.fullmatch(normalized) or normalized.casefold() in repeated:
                continue
            kept.append(line)
        cleaned_pages.append("\n".join(kept).strip())
    return "\n\n".join(page for page in cleaned_pages if page)


def _load_docx(raw_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in document.paragraphs)
