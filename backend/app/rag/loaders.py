"""Document loaders: extract raw text from PDF, DOCX, and TXT/MD files."""
import io
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
    return "\n\n".join(pages)


def _load_docx(raw_bytes: bytes) -> str:
    document = docx.Document(io.BytesIO(raw_bytes))
    return "\n".join(p.text for p in document.paragraphs)
