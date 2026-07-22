"""Отправка сообщений в Telegram без зависимости от aiogram (для ETL и рассылок)."""

import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)


async def send_message(chat_id: int, text: str) -> bool:
    """Отправить сообщение конкретному пользователю/чату. False, если не удалось/нет токена."""
    if not settings.bot_token:
        log.info("сообщение (токен не настроен) -> %s: %s", chat_id, text)
        return False
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            )
            return response.status_code == 200
    except httpx.HTTPError:
        log.exception("не удалось отправить сообщение в чат %s", chat_id)
        return False


async def notify_admin(text: str) -> None:
    if settings.admin_chat_id is None:
        log.info("админ-уведомление (чат не настроен): %s", text)
        return
    await send_message(settings.admin_chat_id, text)
