from __future__ import annotations

from pathlib import Path

import httpx

from orchestrator_api.core.settings import Settings, get_settings

_RULES_PATH = Path(__file__).resolve().parent / "normalize_rules.md"
_MAX_INPUT_CHARS = 80_000


def load_normalize_rules() -> str:
    return _RULES_PATH.read_text(encoding="utf-8")


def _strip_markdown_fence(text: str) -> str:
    s = text.strip()
    if not s.startswith("```"):
        return s
    lines = s.split("\n")
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines).strip()


async def normalize_to_markdown(
    *,
    raw_text: str,
    title: str | None = None,
    settings: Settings | None = None,
) -> tuple[str, str]:
    """
    Переписывает сырой текст в Markdown по normalize_rules.md.
    Returns (markdown, model_name).
    """
    settings = settings or get_settings()
    api_key = (settings.openai_api_key or "").strip()
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required for AI document preparation (orchestrator-api .env)."
        )

    body = raw_text.strip()
    if not body:
        raise ValueError("Empty text.")
    if len(body) > _MAX_INPUT_CHARS:
        body = body[:_MAX_INPUT_CHARS] + "\n\n[… текст обрезан для лимита подготовки …]"

    rules = load_normalize_rules()
    doc_title = (title or "").strip() or "Без названия"
    user_msg = (
        f"Название документа в базе знаний: {doc_title}\n\n"
        f"--- Исходный текст ---\n\n{body}"
    )
    model = settings.knowledge_normalize_model

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": rules},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.1,
    }
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()

    content = str(data["choices"][0]["message"]["content"] or "").strip()
    content = _strip_markdown_fence(content)
    if not content:
        raise RuntimeError("Model returned empty markdown.")
    return content, model
