"""Structure-aware chunking: split on headings/sections first, then by size with overlap."""
import re
from dataclasses import dataclass


@dataclass
class Chunk:
    content: str
    section: str | None
    index: int


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


_HEADING_RE = re.compile(r"^(#{1,3}\s+.+|[A-Z][A-Za-z0-9 /&\-]{3,60}:?)\s*$", re.MULTILINE)


def _split_into_sections(text: str) -> list[tuple[str | None, str]]:
    """Split text into (section_title, section_body) pairs using headings as anchors."""
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [(None, text)]

    sections: list[tuple[str | None, str]] = []
    for i, m in enumerate(matches):
        title = m.group(0).strip("# ").strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            sections.append((title, body))

    # Preserve any preamble before the first heading
    if matches[0].start() > 0:
        preamble = text[: matches[0].start()].strip()
        if preamble:
            sections.insert(0, (None, preamble))

    return sections or [(None, text)]


def chunk_document(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[Chunk]:
    """
    Chunk a document respecting section boundaries where possible, falling back
    to fixed-size sliding windows with overlap within long sections.
    """
    text = clean_text(text)
    sections = _split_into_sections(text)

    chunks: list[Chunk] = []
    idx = 0
    for section_title, body in sections:
        if len(body) <= chunk_size:
            chunks.append(Chunk(content=body, section=section_title, index=idx))
            idx += 1
            continue

        start = 0
        while start < len(body):
            end = min(start + chunk_size, len(body))
            # try to end on a sentence boundary for readability
            if end < len(body):
                last_period = body.rfind(". ", start, end)
                if last_period != -1 and last_period > start + chunk_size * 0.5:
                    end = last_period + 1
            piece = body[start:end].strip()
            if piece:
                chunks.append(Chunk(content=piece, section=section_title, index=idx))
                idx += 1
            if end >= len(body):
                break
            start = max(end - chunk_overlap, start + 1)

    return chunks
