from __future__ import annotations

from pathlib import Path

from vendor_support_agent.core.rag_service import RetrievedChunk
from vendor_support_agent.core.settings import get_settings


def _read(name: str) -> str:
    p = Path(get_settings().prompts_dir) / name
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8").strip()


def build_system_prompt() -> str:
    parts = [
        _read("system.md"),
        _read("answer_policy.md"),
        _read("channel_style.md"),
    ]
    return "\n\n".join([p for p in parts if p]).strip() or "You are a helpful assistant."


def build_user_prompt(*, user_message: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return f"Вопрос пользователя:\n{user_message}\n\nКонтекст: (пусто)"

    ctx_parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        ctx_parts.append(f"[{i}] (document_id={c.document_id}, chunk_id={c.chunk_id}, title={c.title})\n{c.content}")
    ctx = "\n\n".join(ctx_parts)
    return f"Контекст из базы знаний:\n{ctx}\n\nВопрос пользователя:\n{user_message}"
