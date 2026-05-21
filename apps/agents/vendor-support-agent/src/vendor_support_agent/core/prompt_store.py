"""Загрузка актуальных промптов из Postgres (редактируются в Studio / orchestrator-api)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.db.models.prompt import PromptTemplate, PromptVersion

# Базовые блоки (порядок важен), затем остальные ключи из Studio
CORE_PROMPT_KEYS = ("system", "answer_policy", "channel_style", "fallback")
# Только Studio / журнал — не склеиваются в системный промпт ответов пользователю
RUNTIME_EXCLUDED_PROMPT_KEYS = frozenset({"tuning_log"})


async def get_latest_prompt_content(db: AsyncSession, prompt_key: str) -> str | None:
    row = (
        await db.execute(
            select(PromptVersion)
            .where(PromptVersion.prompt_key == prompt_key)
            .order_by(PromptVersion.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return None
    text = (row.content or "").strip()
    return text or None


async def _ordered_prompt_keys(db: AsyncSession) -> list[str]:
    rows = (await db.execute(select(PromptTemplate.prompt_key))).scalars().all()
    all_keys = set(rows)
    ordered: list[str] = [k for k in CORE_PROMPT_KEYS if k in all_keys]
    for k in sorted(all_keys):
        if k not in CORE_PROMPT_KEYS and k not in RUNTIME_EXCLUDED_PROMPT_KEYS:
            ordered.append(k)
    return ordered


async def load_system_prompt_parts(db: AsyncSession) -> list[str]:
    parts: list[str] = []
    for key in await _ordered_prompt_keys(db):
        content = await get_latest_prompt_content(db, key)
        if content:
            parts.append(content)
    return parts
