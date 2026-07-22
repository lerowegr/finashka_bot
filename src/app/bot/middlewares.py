import logging
from collections.abc import Awaitable, Callable
from datetime import datetime
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update

from app.db import models as m
from app.db.engine import session_factory

log = logging.getLogger(__name__)


class DbSessionMiddleware(BaseMiddleware):
    """Одна сессия БД на апдейт, доступна хендлерам как аргумент `session`."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with session_factory() as session:
            data["session"] = session
            return await handler(event, data)


class UserMiddleware(BaseMiddleware):
    """Регистрирует пользователя и обновляет last_seen."""

    async def __call__(self, handler, event: Update, data: dict[str, Any]) -> Any:
        tg_user = data.get("event_from_user")
        session = data.get("session")
        if tg_user is not None and session is not None:
            user = await session.get(m.User, tg_user.id)
            if user is None:
                user = m.User(tg_id=tg_user.id)
                session.add(user)
            user.last_seen_at = datetime.now()
            await session.commit()
        return await handler(event, data)


async def on_error(event, *args, **kwargs) -> bool:
    """Пользователь всегда получает ответ, ошибка — в лог, бот живёт дальше."""
    update = getattr(event, "update", None)
    log.exception("ошибка обработки апдейта: %s", getattr(event, "exception", event))

    target = None
    if update is not None:
        target = update.callback_query or update.message
    if isinstance(target, CallbackQuery):
        try:
            await target.answer("Что-то пошло не так. Попробуйте /start", show_alert=True)
        except Exception:  # noqa: BLE001
            pass
    elif isinstance(target, Message):
        try:
            await target.answer("Что-то пошло не так. Попробуйте /start")
        except Exception:  # noqa: BLE001
            pass
    return True
