from __future__ import annotations


def chunk_text(text: str, *, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    text = text.strip()
    if not text:
        return []

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        piece = text[start:end].strip()
        if not piece:
            start = end
            continue
        chunks.append(piece)
        if end >= n:
            break
        start = max(0, end - overlap)

    return chunks
