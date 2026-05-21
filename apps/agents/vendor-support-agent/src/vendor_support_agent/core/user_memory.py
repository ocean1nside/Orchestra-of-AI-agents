from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from vendor_support_agent.core.llm_client import complete_chat
from vendor_support_agent.core.settings import Settings, get_settings
from vendor_support_agent.db.models.user_fact import RuntimeUserFact
from vendor_support_agent.schemas.invoke import InvokeRequest

logger = logging.getLogger(__name__)

ALLOWED_FACT_KEYS = frozenset(
    {
        "name",
        "phone",
        "email",
        "address",
        "city",
        "company",
        "inn",
        "role",
        "note",
    }
)

FACT_LABELS: dict[str, str] = {
    "name": "Имя / как обращаться",
    "phone": "Телефон",
    "email": "Email",
    "address": "Адрес",
    "city": "Город",
    "company": "Компания / организация",
    "inn": "ИНН",
    "role": "Роль / должность",
    "note": "Прочее",
}

_EXTRACT_SYSTEM = """Ты извлекаешь факты о пользователе из одного сообщения в чат поддержки.
Верни ТОЛЬКО JSON: {"facts": [{"key": "...", "value": "..."}]}
Допустимые key: name, phone, email, address, city, company, inn, role, note.
Правила:
- Только то, что пользователь явно написал о себе (имя, контакты, адрес, компания).
- Не выдумывай. Пустой массив, если фактов нет.
- value — кратко, как в сообщении (телефон в международном или как написал пользователь).
- name — только если представился (меня зовут, я Иван), не имена других людей."""

_NAME_RE = re.compile(
    r"(?:меня\s+зовут|моё\s+имя|мое\s+имя|я\s+—|я\s+-|это\s+)([А-ЯЁA-Z][а-яёa-z\-]{1,40}(?:\s+[А-ЯЁA-Z][а-яёa-z\-]{1,40})?)",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(
    r"(?:\+7|8)[\s\-]?\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{2}[\s\-]?\d{2}\d{0,2}"
)
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_INN_RE = re.compile(r"\b(?:инн|ИНН)\s*[:\s]?\s*(\d{10,12})\b", re.IGNORECASE)
_CITY_RE = re.compile(
    r"(?:город|г\.)\s*([А-ЯЁ][а-яё\-]{2,40})",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(
    r"(?:адрес|находимся|доставк[аи]\s+(?:на|по)|ул\.|улиц[аы])\s*[:\s]?\s*([^\n]{10,120})",
    re.IGNORECASE,
)
_COMPANY_RE = re.compile(
    r"(?:компани[яи]|организаци[яи]|ооо|ип)\s*[:\s]?\s*([^\n,]{2,80})",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class UserFactRow:
    fact_key: str
    fact_value: str
    label: str
    updated_at: datetime | None = None


def _normalize_value(value: str, *, max_len: int = 500) -> str:
    v = " ".join((value or "").split()).strip()
    if len(v) > max_len:
        v = v[: max_len - 1] + "…"
    return v


def _regex_extract(message: str) -> list[tuple[str, str]]:
    text = (message or "").strip()
    if not text:
        return []
    out: list[tuple[str, str]] = []

    m = _NAME_RE.search(text)
    if m:
        out.append(("name", _normalize_value(m.group(1), max_len=80)))

    for m in _PHONE_RE.finditer(text):
        out.append(("phone", _normalize_value(m.group(0), max_len=32)))

    for m in _EMAIL_RE.finditer(text):
        out.append(("email", _normalize_value(m.group(0), max_len=120)))

    m = _INN_RE.search(text)
    if m:
        out.append(("inn", m.group(1)))

    m = _CITY_RE.search(text)
    if m:
        out.append(("city", _normalize_value(m.group(1), max_len=80)))

    m = _ADDRESS_RE.search(text)
    if m:
        out.append(("address", _normalize_value(m.group(1), max_len=200)))

    m = _COMPANY_RE.search(text)
    if m:
        out.append(("company", _normalize_value(m.group(1), max_len=120)))

    return out


def _parse_llm_facts(raw: str) -> list[tuple[str, str]]:
    text = (raw or "").strip()
    if not text:
        return []
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    items = data.get("facts") if isinstance(data, dict) else None
    if not isinstance(items, list):
        return []
    out: list[tuple[str, str]] = []
    for it in items:
        if not isinstance(it, dict):
            continue
        key = str(it.get("key", "")).strip().lower()
        val = _normalize_value(str(it.get("value", "")))
        if key in ALLOWED_FACT_KEYS and val:
            out.append((key, val))
    return out


async def _llm_extract(message: str, *, settings: Settings) -> list[tuple[str, str]]:
    if not (settings.llm_api_key or "").strip():
        return []
    if len(message.strip()) < 8:
        return []
    try:
        raw = await complete_chat(
            system=_EXTRACT_SYSTEM,
            user=f"Сообщение пользователя:\n{message[:4000]}",
            settings=settings,
        )
        return _parse_llm_facts(raw)
    except Exception:
        logger.exception("user fact LLM extract failed")
        return []


def _merge_candidates(*groups: list[tuple[str, str]]) -> list[tuple[str, str]]:
    merged: dict[str, str] = {}
    for group in groups:
        for key, val in group:
            if key in ALLOWED_FACT_KEYS and val:
                merged[key] = val
    return list(merged.items())


async def extract_facts_from_message(message: str, *, settings: Settings | None = None) -> list[tuple[str, str]]:
    settings = settings or get_settings()
    regex_facts = _regex_extract(message)
    if not settings.user_memory_use_llm:
        return regex_facts
    llm_facts = await _llm_extract(message, settings=settings)
    return _merge_candidates(regex_facts, llm_facts)


async def load_user_facts(
    db: AsyncSession, *, channel: str, user_id: str, limit: int = 30
) -> list[UserFactRow]:
    stmt = (
        select(RuntimeUserFact)
        .where(RuntimeUserFact.channel == channel, RuntimeUserFact.user_id == str(user_id))
        .order_by(RuntimeUserFact.updated_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    result: list[UserFactRow] = []
    for r in rows:
        key = (r.fact_key or "").strip().lower()
        if key not in ALLOWED_FACT_KEYS:
            continue
        val = _normalize_value(r.fact_value)
        if not val:
            continue
        result.append(
            UserFactRow(
                fact_key=key,
                fact_value=val,
                label=FACT_LABELS.get(key, key),
                updated_at=r.updated_at,
            )
        )
    return result


async def upsert_user_facts(
    db: AsyncSession,
    *,
    channel: str,
    user_id: str,
    conversation_id: str | None,
    candidates: list[tuple[str, str]],
    source: str = "extracted",
) -> int:
    if not candidates:
        return 0
    now = datetime.utcnow()
    n = 0
    for key, val in candidates:
        key = key.strip().lower()
        val = _normalize_value(val)
        if key not in ALLOWED_FACT_KEYS or not val:
            continue
        existing = (
            await db.execute(
                select(RuntimeUserFact).where(
                    RuntimeUserFact.channel == channel,
                    RuntimeUserFact.user_id == str(user_id),
                    RuntimeUserFact.fact_key == key,
                )
            )
        ).scalar_one_or_none()
        if existing is None:
            db.add(
                RuntimeUserFact(
                    id=f"ufact_{uuid4().hex}",
                    channel=channel,
                    user_id=str(user_id),
                    fact_key=key,
                    fact_value=val,
                    source=source,
                    conversation_id=conversation_id,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            if existing.fact_value != val:
                existing.fact_value = val
                existing.updated_at = now
                existing.conversation_id = conversation_id
                existing.source = source
        n += 1
    await db.commit()
    return n


async def refresh_user_memory_from_message(
    db: AsyncSession,
    *,
    req: InvokeRequest,
    conversation_id: str,
    settings: Settings | None = None,
) -> list[UserFactRow]:
    """Извлечь факты из текущего сообщения, сохранить, вернуть все факты пользователя."""
    settings = settings or get_settings()
    if not settings.user_memory_enabled:
        return []
    candidates = await extract_facts_from_message(req.message, settings=settings)
    if candidates:
        await upsert_user_facts(
            db,
            channel=req.channel,
            user_id=str(req.user_id),
            conversation_id=conversation_id,
            candidates=candidates,
        )
    return await load_user_facts(db, channel=req.channel, user_id=str(req.user_id), limit=settings.user_memory_max_facts)


def format_user_facts_block(facts: list[UserFactRow]) -> str:
    if not facts:
        return ""
    lines = [f"- {f.label}: {f.fact_value}" for f in facts]
    return (
        "Известные данные о пользователе (из прошлых сообщений; используй для обращения и уточнений, "
        "не выдумывай новые контакты и имена):\n"
        + "\n".join(lines)
    )


async def prune_old_facts(db: AsyncSession, *, channel: str, user_id: str, keep: int) -> None:
    rows = list(
        (
            await db.execute(
                select(RuntimeUserFact)
                .where(RuntimeUserFact.channel == channel, RuntimeUserFact.user_id == str(user_id))
                .order_by(RuntimeUserFact.updated_at.desc())
            )
        ).scalars().all()
    )
    if len(rows) <= keep:
        return
    for old in rows[keep:]:
        await db.execute(delete(RuntimeUserFact).where(RuntimeUserFact.id == old.id))
    await db.commit()
