import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import catalog, compare, ege, favorites, profile, start, universities
from app.bot.middlewares import DbSessionMiddleware, UserMiddleware, on_error
from app.config import settings
from app.db.engine import create_schema, session_factory
from app.logsetup import setup_logging

log = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    """Собрать диспетчер. Вынесено отдельно, чтобы тестировать без сети и токена."""
    dp = Dispatcher(storage=MemoryStorage())

    for observer in (dp.message, dp.callback_query):
        observer.middleware(DbSessionMiddleware())
        observer.middleware(UserMiddleware())

    dp.include_router(start.router)
    dp.include_router(profile.router)
    dp.include_router(catalog.router)
    dp.include_router(ege.router)
    dp.include_router(universities.router)
    dp.include_router(compare.router)
    dp.include_router(favorites.router)

    dp.errors.register(on_error)
    return dp


async def _startup() -> None:
    """Готовим БД к работе: создаём схему (чтобы свежий клон работал без db-init)
    и предупреждаем, если данные ещё не загружены."""
    from sqlalchemy import func, select

    from app.db import models as m

    await create_schema()
    async with session_factory() as session:
        universities = (
            await session.execute(select(func.count()).select_from(m.University))
        ).scalar()
    if not universities:
        log.warning(
            "В базе нет вузов — каталог будет пустым. "
            "Наполните данными командой: python -m app.cli etl light"
        )


async def main() -> None:
    setup_logging("bot")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан. Укажите его в .env (см. .env.example).")

    await _startup()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = build_dispatcher()
    log.info("Бот запущен, начинаю polling")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
