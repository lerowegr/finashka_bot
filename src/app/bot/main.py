import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.bot.handlers import catalog, ege, favorites, profile, start, universities
from app.bot.middlewares import DbSessionMiddleware, UserMiddleware, on_error
from app.config import settings
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
    dp.include_router(favorites.router)

    dp.errors.register(on_error)
    return dp


async def main() -> None:
    setup_logging("bot")
    if not settings.bot_token:
        raise SystemExit("BOT_TOKEN не задан. Укажите его в .env (см. .env.example).")

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
