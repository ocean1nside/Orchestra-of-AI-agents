from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from orchestrator_api.core.settings import Settings, get_settings
from orchestrator_api.db.models.prompt import PromptTemplate, PromptVersion
from orchestrator_api.schemas.prompts import PromptTuneAppliedItem, PromptTuneChange

_RULES_PATH = Path(__file__).resolve().parent / "prompt_tune_rules.md"
_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_MAX_FEEDBACK_CHARS = 8_000
_MAX_PROMPTS_JSON_CHARS = 120_000
TUNING_LOG_KEY = "tuning_log"


def load_tune_rules() -> str:
    return _RULES_PATH.read_text(encoding="utf-8")


def _strip_json_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


async def load_prompts_snapshot(db: AsyncSession) -> dict[str, str]:
    templates = (await db.execute(select(PromptTemplate))).scalars().all()
    out: dict[str, str] = {}
    for t in templates:
        row = (
            await db.execute(
                select(PromptVersion)
                .where(PromptVersion.prompt_key == t.prompt_key)
                .order_by(PromptVersion.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if row and (row.content or "").strip():
            out[t.prompt_key] = row.content.strip()
    return out


async def ensure_tuning_log_template(db: AsyncSession) -> None:
    exists = (
        await db.execute(select(PromptTemplate).where(PromptTemplate.prompt_key == TUNING_LOG_KEY))
    ).scalar_one_or_none()
    if exists is not None:
        return
    now = datetime.utcnow()
    db.add(
        PromptTemplate(
            prompt_key=TUNING_LOG_KEY,
            description="Журнал автотюнинга Studio (не уходит в ответы бота)",
            created_at=now,
        )
    )
    db.add(
        PromptVersion(
            id=f"pv_{uuid4().hex}",
            prompt_key=TUNING_LOG_KEY,
            version=1,
            content="Журнал правок промптов через вкладку «Тюнинг».\n",
            created_at=now,
        )
    )
    await db.commit()


async def _put_prompt_version(db: AsyncSession, *, prompt_key: str, content: str) -> int:
    latest = (
        await db.execute(
            select(func.max(PromptVersion.version)).where(PromptVersion.prompt_key == prompt_key)
        )
    ).scalar_one()
    next_ver = int(latest or 0) + 1
    pv = PromptVersion(
        id=f"pv_{uuid4().hex}",
        prompt_key=prompt_key,
        version=next_ver,
        content=content.strip(),
        created_at=datetime.utcnow(),
    )
    db.add(pv)
    return next_ver


async def _create_prompt_template(
    db: AsyncSession, *, prompt_key: str, description: str, content: str
) -> int:
    now = datetime.utcnow()
    db.add(
        PromptTemplate(
            prompt_key=prompt_key,
            description=description,
            created_at=now,
        )
    )
    pv = PromptVersion(
        id=f"pv_{uuid4().hex}",
        prompt_key=prompt_key,
        version=1,
        content=content.strip(),
        created_at=now,
    )
    db.add(pv)
    return 1


def _validate_changes(
    changes: list[dict],
    *,
    existing_keys: set[str],
) -> list[PromptTuneChange]:
    out: list[PromptTuneChange] = []
    for raw in changes:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get("prompt_key", "")).strip()
        action = str(raw.get("action", "update")).strip().lower()
        content = str(raw.get("content", "")).strip()
        rationale = str(raw.get("rationale", "")).strip()
        if not key or not _KEY_RE.match(key):
            continue
        if key == TUNING_LOG_KEY:
            continue
        if not content:
            continue
        if action not in ("update", "create"):
            action = "update"
        if action == "create" and key in existing_keys:
            action = "update"
        if action == "update" and key not in existing_keys:
            action = "create"
        out.append(
            PromptTuneChange(
                prompt_key=key,
                action=action,
                content=content,
                rationale=rationale or "—",
            )
        )
    return out


async def propose_prompt_tune(
    db: AsyncSession,
    *,
    feedback: str,
    settings: Settings | None = None,
) -> tuple[str, str, list[PromptTuneChange], str]:
    """
    Returns (summary, log_entry, changes, model_name).
    """
    settings = settings or get_settings()
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for prompt tuning (orchestrator-api .env)."
        )

    fb = feedback.strip()
    if not fb:
        raise ValueError("Feedback is empty.")
    if len(fb) > _MAX_FEEDBACK_CHARS:
        fb = fb[:_MAX_FEEDBACK_CHARS] + "\n[… обрезано …]"

    snapshot = await load_prompts_snapshot(db)
    prompts_json = json.dumps(snapshot, ensure_ascii=False, indent=2)
    if len(prompts_json) > _MAX_PROMPTS_JSON_CHARS:
        prompts_json = prompts_json[:_MAX_PROMPTS_JSON_CHARS] + "\n…"

    user_msg = (
        f"--- Жалоба оператора ---\n{fb}\n\n"
        f"--- Текущие блоки (JSON, ключ → полный текст) ---\n{prompts_json}"
    )
    model = settings.prompt_tune_model
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": load_tune_rules()},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

    raw = _strip_json_fence(str(data["choices"][0]["message"]["content"] or ""))
    parsed = json.loads(raw)
    summary = str(parsed.get("summary", "")).strip() or "Правки предложены."
    log_entry = str(parsed.get("log_entry", "")).strip()
    changes = _validate_changes(
        parsed.get("changes") if isinstance(parsed.get("changes"), list) else [],
        existing_keys=set(snapshot.keys()),
    )
    return summary, log_entry, changes, model


async def apply_prompt_tune(
    db: AsyncSession,
    *,
    changes: list[PromptTuneChange],
    log_entry: str,
) -> list[PromptTuneAppliedItem]:
    await ensure_tuning_log_template(db)
    applied: list[PromptTuneAppliedItem] = []

    for ch in changes:
        if ch.prompt_key == TUNING_LOG_KEY:
            continue
        exists = (
            await db.execute(
                select(PromptTemplate).where(PromptTemplate.prompt_key == ch.prompt_key)
            )
        ).scalar_one_or_none()
        if ch.action == "create" and exists is None:
            ver = await _create_prompt_template(
                db,
                prompt_key=ch.prompt_key,
                description=ch.rationale[:500] or ch.prompt_key,
                content=ch.content,
            )
        elif exists is not None:
            ver = await _put_prompt_version(db, prompt_key=ch.prompt_key, content=ch.content)
        else:
            ver = await _create_prompt_template(
                db,
                prompt_key=ch.prompt_key,
                description=ch.rationale[:500] or ch.prompt_key,
                content=ch.content,
            )
        applied.append(
            PromptTuneAppliedItem(
                prompt_key=ch.prompt_key,
                action=ch.action,
                version=ver,
                rationale=ch.rationale,
            )
        )

    entry = (log_entry or "").strip()
    if entry:
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        block = f"[{ts}]\n{entry}"
        row = (
            await db.execute(
                select(PromptVersion)
                .where(PromptVersion.prompt_key == TUNING_LOG_KEY)
                .order_by(PromptVersion.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        prev = (row.content or "").strip() if row else ""
        new_log = (prev + "\n\n" + block).strip() + "\n"
        log_ver = await _put_prompt_version(db, prompt_key=TUNING_LOG_KEY, content=new_log)
        applied.append(
            PromptTuneAppliedItem(
                prompt_key=TUNING_LOG_KEY,
                action="update",
                version=log_ver,
                rationale="Запись в журнал тюнинга",
            )
        )

    await db.commit()
    return applied
