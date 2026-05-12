"""Эскалация в Telegram-группу операторов со всех каналов (widget / telegram / max)."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import quote

from vendor_support_agent.core.settings import Settings
from vendor_support_agent.core.telegram_outbound import send_message
from vendor_support_agent.schemas.invoke import InvokeRequest

logger = logging.getLogger(__name__)

_USER_ESCALATION_PHRASES = (
    "оператор",
    "живой человек",
    "реальный человек",
    "менеджер",
    "эскалац",
    "позовите",
    "позови ",
    "соедини",
    "соедините",
    "переключи на человека",
    "не бот",
    "человеку",
    "саппорт",
    "поддержк",  # поддержка, поддержку
    "жалоб",
    "руководител",
    "специалист",
    "human agent",
    "speak to a human",
    "talk to human",
    "escalate",
)


def parse_escalation_telegram_chat_id(settings: Settings) -> int | None:
    """ID группы для уведомлений эскалации (-100…). Некорректное значение — None."""
    raw = (settings.escalation_telegram_chat_id or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        logger.error("invalid ESCALATION_TELEGRAM_CHAT_ID: %r", raw)
        return None


# Срабатывают только при умеренной уверенности RAG (см. compute_escalation).
_ANSWER_HEDGE_PHRASES = (
    "не уверен",
    "не могу подтвердить",
    "недостаточно информации в контексте",
    "недостаточно данных в контексте",
    "в переданных фрагментах нет",
    "в выданном контексте нет",
    "не могу ответить уверенно",
)


def user_requests_escalation(message: str) -> bool:
    t = message.lower().strip()
    if not t:
        return False
    if re.search(r"\bоператор\b", t):
        return True
    return any(p in t for p in _USER_ESCALATION_PHRASES)


def answer_signals_uncertainty(answer: str) -> bool:
    a = answer.lower()
    return any(p in a for p in _ANSWER_HEDGE_PHRASES)


def build_quick_chat_link(*, settings: Settings, req: InvokeRequest) -> str:
    """Ссылка для операторов: для Telegram — t.me/c/… при -100…; иначе заглушка с параметрами."""
    if req.channel == "telegram":
        try:
            cid = int(str(req.conversation_id).strip())
            s = str(cid)
            if s.startswith("-100") and len(s) > 4:
                return f"https://t.me/c/{s[4:]}/"
            if cid > 0:
                try:
                    uid = int(str(req.user_id).strip())
                    return f"tg://user?id={uid}"
                except ValueError:
                    pass
        except (TypeError, ValueError):
            pass
    base = (settings.escalation_context_base_url or "").strip().rstrip("/")
    if not base:
        base = "https://example.com/support-context"
    q = quote(req.conversation_id, safe="")
    u = quote(str(req.user_id), safe="")
    return f"{base}?channel={req.channel}&conversation_id={q}&user_id={u}"


@dataclass
class EscalationDecision:
    should_escalate: bool
    reasons: list[str] = field(default_factory=list)


def compute_escalation(
    *,
    settings: Settings,
    message: str,
    answer: str,
    confidence: float,
    needs_human: bool,
) -> EscalationDecision:
    reasons: list[str] = []
    if user_requests_escalation(message):
        reasons.append("user_request")
    if needs_human or confidence < 0.28:
        reasons.append("low_rag_confidence")
    elif confidence < 0.45 and answer_signals_uncertainty(answer):
        reasons.append("hedged_answer")

    # Уникальные, стабильный порядок
    seen: set[str] = set()
    uniq = []
    for r in reasons:
        if r not in seen:
            seen.add(r)
            uniq.append(r)

    chat = (settings.escalation_telegram_chat_id or "").strip()
    should = bool(uniq) and bool(chat)
    return EscalationDecision(should_escalate=should, reasons=uniq)


def append_escalation_user_notice(answer: str, decision: EscalationDecision) -> str:
    if not decision.should_escalate:
        return answer
    base = answer.rstrip()
    if "user_request" in decision.reasons:
        note = (
            "Запрос передан в службу поддержки — коллеги увидят диалог и смогут подключиться "
            "при первой возможности."
        )
    elif "low_rag_confidence" in decision.reasons or "hedged_answer" in decision.reasons:
        note = (
            "По базе знаний ответ может быть неполным; коллеги из поддержки также получили уведомление "
            "и смогут уточнить детали."
        )
    else:
        note = "Коллеги из поддержки получили уведомление по этому обращению."
    if not base:
        return note
    return f"{base}\n\n{note}"


USER_REQUEST_ESCALATION_ACK = (
    "Я передал запрос оператору. Коллеги из поддержки ответят вам здесь, как только смогут."
)


def format_user_facing_answer(*, llm_answer: str, decision: EscalationDecision) -> str:
    """
    Текст пользователю после эскалации.
    Явный запрос оператора — короткое подтверждение без «воды» из модели.
    """
    if decision.should_escalate and "user_request" in decision.reasons:
        return USER_REQUEST_ESCALATION_ACK
    return append_escalation_user_notice(llm_answer, decision)


def _reason_labels(reasons: list[str]) -> str:
    labels = []
    for r in reasons:
        if r == "user_request":
            labels.append("явный запрос оператора / эскалации")
        elif r == "low_rag_confidence":
            labels.append("низкая релевантность источников (RAG)")
        elif r == "hedged_answer":
            labels.append("осторожная / неуверенная формулировка ответа")
        else:
            labels.append(r)
    return "; ".join(labels) if labels else "—"


async def send_escalation_notification(
    *,
    settings: Settings,
    req: InvokeRequest,
    user_message: str,
    answer: str,
    confidence: float,
    decision: EscalationDecision,
) -> None:
    if not decision.should_escalate:
        return
    token = (settings.telegram_bot_token or "").strip()
    if not token:
        logger.warning("escalation skipped: TELEGRAM_BOT_TOKEN is empty")
        return
    dest = parse_escalation_telegram_chat_id(settings)
    if dest is None:
        return

    link = build_quick_chat_link(settings=settings, req=req)
    um = user_message.strip() or "—"
    ans = (answer or "").strip() or "—"
    if len(um) > 1200:
        um = um[:1180] + "\n…(обрезано)"
    if len(ans) > 1600:
        ans = ans[:1580] + "\n…(обрезано)"

    text = (
        "🚨 Эскалация vendor-support\n\n"
        f"Канал: {req.channel}\n"
        f"user_id: {req.user_id}\n"
        f"conversation_id: {req.conversation_id}\n"
        f"Уверенность RAG (эвристика): {confidence:.2f}\n"
        f"Причина: {_reason_labels(decision.reasons)}\n\n"
        f"Сообщение пользователя:\n{um}\n\n"
        f"Ответ агента (черновик):\n{ans}\n\n"
        f"Быстрый контекст / чат:\n{link}"
    )

    try:
        await send_message(bot_token=token, chat_id=dest, text=text)
    except Exception:
        logger.exception("escalation sendMessage failed chat_id=%s", dest)
