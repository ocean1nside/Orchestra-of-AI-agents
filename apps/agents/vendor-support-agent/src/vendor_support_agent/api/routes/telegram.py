from __future__ import annotations

import asyncio
import logging
from contextlib import suppress

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import ValidationError

from vendor_support_agent.core.agent_engine import AgentEngine
from vendor_support_agent.core.escalation import parse_escalation_telegram_chat_id
from vendor_support_agent.core.settings import get_settings
from vendor_support_agent.core.telegram_outbound import (
    edit_message_text,
    send_chat_action,
    send_message,
    send_message_get_id,
)
from vendor_support_agent.schemas.invoke import InvokeRequest
from vendor_support_agent.schemas.telegram import TelegramUpdate

logger = logging.getLogger(__name__)

router = APIRouter()
_engine = AgentEngine()

_WELCOME = (
    "Привет! Я отвечаю на вопросы по базе знаний (документация продукта).\n\n"
    "Напишите вопрос обычным текстом — я поищу релевантные фрагменты и сформулирую ответ.\n"
    "Справка: /help"
)

_HELP = (
    "Как пользоваться:\n"
    "• Напишите вопрос сообщением — поиск по загруженным документам (RAG).\n"
    "• Если в базе нет данных, скажу об этом честно, без выдумывания.\n"
    "• Нужен человек — напишите, например: «оператор» или «эскалация» (уведомление уйдёт в поддержку, если она настроена).\n"
    "• /start — приветствие.\n\n"
    "Вопросы по настройке бота — к администратору окружения."
)


def _parse_command(text: str) -> tuple[str | None, str]:
    """Первое слово вида /name или /name@bot → (name в lower, хвост первой строки)."""
    first_line = text.strip().split("\n", 1)[0].strip()
    if not first_line.startswith("/"):
        return None, text
    parts = first_line.split(None, 1)
    head = parts[0]
    if "@" in head:
        head = head.split("@", 1)[0]
    if not head.startswith("/"):
        return None, text
    name = head[1:].lower()
    if not name:
        return None, text
    return name, parts[1] if len(parts) > 1 else ""


async def _keep_typing(stop: asyncio.Event, *, bot_token: str, chat_id: int) -> None:
    while not stop.is_set():
        with suppress(Exception):
            await send_chat_action(bot_token=bot_token, chat_id=chat_id, action="typing")
        try:
            await asyncio.wait_for(stop.wait(), timeout=4.0)
        except asyncio.TimeoutError:
            continue


def _typewriter_steps(text_len: int) -> tuple[int, float]:
    """Шаг символов и пауза между edit; короткие ответы — одним сообщением без «набора»."""
    if text_len <= 480:
        return text_len, 0.0
    if text_len <= 2400:
        return 72, 0.035
    return 120, 0.045


async def _reply_llm_then_typewriter(
    *,
    bot_token: str,
    chat_id: int,
    req: InvokeRequest,
) -> None:
    """
    Сначала полный ответ от LLM (пока только «печатает» в чате), затем одно сообщение в чате
    и быстрый набор через editMessageText — без sendMessageDraft + sendMessage (два пузыря).
    """
    stop = asyncio.Event()
    typing_task = asyncio.create_task(_keep_typing(stop, bot_token=bot_token, chat_id=chat_id))
    try:
        resp = await _engine.invoke(req)
        if resp.meta.ai_muted:
            return
        answer = (resp.answer or "").strip() or "Пустой ответ модели."
    finally:
        stop.set()
        typing_task.cancel()
        with suppress(asyncio.CancelledError):
            await typing_task

    step, delay = _typewriter_steps(len(answer))
    if step >= len(answer):
        await send_message(bot_token=bot_token, chat_id=chat_id, text=answer)
        return

    first = answer[:step]
    mid = await send_message_get_id(bot_token=bot_token, chat_id=chat_id, text=first)
    pos = step
    while pos < len(answer):
        pos = min(len(answer), pos + step)
        if delay > 0:
            await asyncio.sleep(delay)
        await edit_message_text(bot_token=bot_token, chat_id=chat_id, message_id=mid, text=answer[:pos])


@router.post("/api/v1/telegram/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(
        default=None,
        alias="X-Telegram-Bot-Api-Secret-Token",
    ),
) -> dict[str, bool]:
    """
    Реальный вебхук Telegram: тело — Update JSON.
    Ответ: сначала полная генерация (статус «печатает»), затем одно сообщение и при длинном тексте
    быстрый набор через editMessageText (без второго пузыря от draft+send).
    """
    settings = get_settings()
    token = settings.telegram_bot_token.strip()
    if not token:
        raise HTTPException(status_code=503, detail="TELEGRAM_BOT_TOKEN is not configured")

    secret = (settings.telegram_webhook_secret or "").strip()
    if secret and x_telegram_bot_api_secret_token != secret:
        raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        body = await request.json()
    except Exception:
        return {"ok": True}

    try:
        upd = TelegramUpdate.model_validate(body)
    except ValidationError:
        return {"ok": True}

    msg = upd.message or upd.edited_message
    if not msg:
        return {"ok": True}

    # Группа только для уведомлений эскалации: не обрабатывать как диалог с пользователем.
    esc_chat = parse_escalation_telegram_chat_id(settings)
    if esc_chat is not None and msg.chat.id == esc_chat:
        logger.info("telegram webhook ignored (escalation ops chat) chat_id=%s", esc_chat)
        return {"ok": True}

    if not msg.text or not (text := msg.text.strip()):
        return {"ok": True}

    cmd, _rest = _parse_command(text)
    if cmd == "start":
        await send_message(bot_token=token, chat_id=msg.chat.id, text=_WELCOME)
        return {"ok": True}
    if cmd == "help":
        await send_message(bot_token=token, chat_id=msg.chat.id, text=_HELP)
        return {"ok": True}
    if cmd is not None:
        await send_message(
            bot_token=token,
            chat_id=msg.chat.id,
            text=(
                f"Команда /{cmd} здесь не используется — я отвечаю на вопросы по базе знаний обычным текстом.\n"
                "Сформулируйте запрос без слэша или откройте /help."
            ),
        )
        return {"ok": True}

    uid = str(msg.from_user.id) if msg.from_user else str(msg.chat.id)
    req = InvokeRequest(
        channel="telegram",
        conversation_id=str(msg.chat.id),
        user_id=uid,
        message=text,
    )

    try:
        await _reply_llm_then_typewriter(bot_token=token, chat_id=msg.chat.id, req=req)
    except Exception:
        logger.exception("telegram webhook handling failed")
        try:
            await send_message(
                bot_token=token,
                chat_id=msg.chat.id,
                text="Не удалось обработать сообщение. Попробуйте позже.",
            )
        except Exception:
            logger.exception("telegram sendMessage after error failed")

    return {"ok": True}
