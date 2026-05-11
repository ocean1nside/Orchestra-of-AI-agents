from __future__ import annotations

import httpx

from vendor_support_agent.core.settings import Settings, get_settings


async def complete_chat(*, system: str, user: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()

    if not settings.llm_api_key.strip():
        # Dev-friendly mock: summarize retrieved context without hallucinating external facts.
        return (
            "Ответ (mock LLM, без LLM_API_KEY): я могу опираться только на переданный контекст. "
            "Кратко: в предоставленных фрагментах содержится релевантная информация по запросу; "
            "для точной формулировки включите LLM_API_KEY.\n\n"
            f"Запрос пользователя:\n{user[:2000]}"
        )

    model = settings.llm_model or "gpt-4o-mini"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.llm_api_key}"},
            json=payload,
        )
        r.raise_for_status()
        data = r.json()
    return str(data["choices"][0]["message"]["content"]).strip()
