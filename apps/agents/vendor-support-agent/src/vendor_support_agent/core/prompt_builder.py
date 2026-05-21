from __future__ import annotations

from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.prompt_store import CORE_PROMPT_KEYS, load_system_prompt_parts
from vendor_support_agent.core.rag_service import RetrievedChunk
from vendor_support_agent.core.user_memory import UserFactRow, format_user_facts_block
from vendor_support_agent.core.settings import get_settings


def _read_file(name: str) -> str:
    p = Path(get_settings().prompts_dir) / name
    if not p.is_file():
        return ""
    return p.read_text(encoding="utf-8").strip()


def _file_fallback_system_prompt() -> str:
    parts = [_read_file(f"{key}.md") for key in CORE_PROMPT_KEYS]
    return "\n\n".join([p for p in parts if p]).strip() or "You are a helpful assistant."


async def build_system_prompt(db: AsyncSession | None = None) -> str:
    """Сначала Postgres (Studio), иначе файлы в prompts_dir."""
    if db is not None:
        parts = await load_system_prompt_parts(db)
        if parts:
            return "\n\n".join(parts)
    return _file_fallback_system_prompt()


def build_user_prompt(
    *,
    user_message: str,
    chunks: list[RetrievedChunk],
    user_facts: list[UserFactRow] | None = None,
) -> str:
    parts: list[str] = []
    facts_block = format_user_facts_block(user_facts or [])
    if facts_block:
        parts.append(facts_block)

    if not chunks:
        parts.append(f"Вопрос пользователя:\n{user_message}\n\nКонтекст базы знаний: (пусто)")
        return "\n\n".join(parts)

    ctx_parts: list[str] = []
    for i, c in enumerate(chunks, start=1):
        ctx_parts.append(f"[{i}] (document_id={c.document_id}, chunk_id={c.chunk_id}, title={c.title})\n{c.content}")
    ctx = "\n\n".join(ctx_parts)
    parts.append(
        "Ниже — извлечённые фрагменты из базы знаний. Опирайся на них при ответе.\n"
        "Если в фрагментах есть шаги, названия экранов или термины по теме вопроса — опиши их; "
        "не пиши «в базе нет информации», если соответствующие сведения явно присутствуют в тексте фрагментов.\n"
        "Если по теме вопроса во фрагментах действительно ничего нет — так и скажи.\n"
        "Если известны имя или контакты пользователя — обращайся по имени, не переспрашивай то, что уже в блоке «Известные данные».\n\n"
        f"{ctx}\n\nВопрос пользователя:\n{user_message}"
    )
    return "\n\n".join(parts)
