from __future__ import annotations

import re

# Порядок важен: от крупных границ к мелким (как RecursiveCharacterTextSplitter).
_DEFAULT_SEPARATORS: tuple[str, ...] = (
    "\n\n\n",
    "\n\n",
    "\n",
    ". ",
    "? ",
    "! ",
    "; ",
    " ",
    "",
)

_SECTION_RE = re.compile(r"^## .+$", re.MULTILINE)


def chunk_text(text: str, *, max_chars: int = 1000, overlap: int = 0) -> list[str]:
    """
    Универсальная нарезка (не-Markdown). overlap по умолчанию 0 — без дублирования хвостов в UI.
    """
    text = text.strip()
    if not text:
        return []

    pieces = _recursive_split(text, list(_DEFAULT_SEPARATORS), max_chars)
    if overlap > 0 and len(pieces) > 1:
        pieces = _apply_overlap(pieces, overlap)
    return [p.strip() for p in pieces if p.strip()]


def chunk_markdown(text: str, *, max_chars: int = 1000) -> list[str]:
    """
    Нарезка Markdown: сначала разделы ##, внутри — абзацы (\\n\\n).
    Каждый чанк сохраняет заголовок раздела; overlap не используется.
    """
    text = text.strip()
    if not text:
        return []

    doc_title = ""
    body = text
    if body.startswith("# ") and not body.startswith("## "):
        first_line, _, rest = body.partition("\n")
        doc_title = first_line.strip()
        body = rest.strip()

    sections = _split_h2_sections(body)
    if not sections:
        return chunk_text(text, max_chars=max_chars, overlap=0)

    chunks: list[str] = []
    for heading, content in sections:
        label = heading or doc_title
        if heading and content:
            section_core = f"{heading}\n\n{content}"
        elif heading:
            section_core = heading
        else:
            section_core = content

        if len(section_core) <= max_chars:
            chunks.append(_attach_doc_title(doc_title, section_core, heading))
            continue

        blocks = [b.strip() for b in content.split("\n\n") if b.strip()] if content else []
        if not blocks:
            chunks.extend(chunk_text(section_core, max_chars=max_chars, overlap=0))
            continue

        buffer = heading or ""
        for block in blocks:
            candidate = f"{buffer}\n\n{block}".strip() if buffer else block
            if len(candidate) <= max_chars:
                buffer = candidate
                continue
            if buffer.strip() and buffer.strip() != heading:
                chunks.append(_attach_doc_title(doc_title, buffer.strip(), heading))
            if len(block) > max_chars:
                for piece in chunk_text(f"{heading}\n\n{block}" if heading else block, max_chars=max_chars, overlap=0):
                    chunks.append(_attach_doc_title(doc_title, piece, heading))
                buffer = heading or ""
            else:
                buffer = f"{heading}\n\n{block}".strip() if heading else block

        if buffer.strip() and (not heading or buffer.strip() != heading):
            chunks.append(_attach_doc_title(doc_title, buffer.strip(), heading))

    return [c for c in chunks if c.strip()]


def choose_chunks(text: str, *, file_format: str = "", ai_normalized: bool = False) -> list[str]:
    fmt = (file_format or "").lower().lstrip(".")
    if ai_normalized or fmt in {"md", "markdown"}:
        return chunk_markdown(text)
    return chunk_text(text, overlap=0)


def _split_h2_sections(body: str) -> list[tuple[str, str]]:
    body = body.strip()
    if not body:
        return []

    if not _SECTION_RE.search(body):
        return [("", body)]

    parts = re.split(r"\n(?=## )", body)
    out: list[tuple[str, str]] = []
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if part.startswith("## "):
            lines = part.split("\n", 1)
            out.append((lines[0].strip(), lines[1].strip() if len(lines) > 1 else ""))
        else:
            out.append(("", part))
    return out


def _attach_doc_title(doc_title: str, chunk: str, section_heading: str) -> str:
    """Добавляет # заголовок документа, если в чанке нет контекста верхнего уровня."""
    if not doc_title:
        return chunk
    if chunk.startswith(doc_title):
        return chunk
    if section_heading and chunk.startswith(section_heading):
        return f"{doc_title}\n\n{chunk}"
    if chunk.startswith("## "):
        return f"{doc_title}\n\n{chunk}"
    return f"{doc_title}\n\n{chunk}"


def _pick_separator(text: str, separators: list[str]) -> str:
    for sep in separators:
        if sep == "":
            return ""
        if sep in text:
            return sep
    return ""


def _recursive_split(text: str, separators: list[str], max_chars: int) -> list[str]:
    text = text.strip()
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    sep = _pick_separator(text, separators)
    try:
        sep_index = separators.index(sep)
    except ValueError:
        sep_index = len(separators) - 1
    finer = separators[sep_index + 1 :] if sep_index + 1 < len(separators) else [""]

    if sep == "":
        return _char_split(text, max_chars)

    parts = text.split(sep)
    if len(parts) == 1:
        return _recursive_split(text, finer, max_chars)

    merged: list[str] = []
    buffer = ""

    for part in parts:
        part = part.strip()
        if not part:
            continue
        piece = f"{buffer}{sep}{part}" if buffer else part
        if len(piece) <= max_chars:
            buffer = piece
            continue
        if buffer:
            merged.append(buffer)
            buffer = ""
        if len(part) > max_chars:
            merged.extend(_recursive_split(part, finer, max_chars))
        else:
            buffer = part

    if buffer:
        merged.append(buffer)
    return merged


def _char_split(text: str, max_chars: int) -> list[str]:
    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= n:
            break
        start = end
    return chunks


def _apply_overlap(chunks: list[str], overlap: int) -> list[str]:
    if overlap <= 0 or len(chunks) < 2:
        return chunks
    out = [chunks[0]]
    for i in range(1, len(chunks)):
        prev = chunks[i - 1]
        prefix = prev[-overlap:] if len(prev) > overlap else prev
        cur = chunks[i]
        if prefix and not cur.startswith(prefix):
            out.append(prefix + cur)
        else:
            out.append(cur)
    return out
