"""Отправка служебных сообщений в админ-чат без зависимости от aiogram."""

import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)


async def notify_admin(text: str) -> None:
    if not settings.bot_token or not settings.admin_chat_id:
        log.info("админ-уведомление (чат не настроен): %s", text)
        return
    url = f"https://api.telegram.org/bot{settings.bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            await client.post(
                url, json={"chat_id": settings.admin_chat_id, "text": text, "parse_mode": "HTML"}
            )
    except httpx.HTTPError:
        log.exception("не удалось отправить уведомление в админ-чат")
