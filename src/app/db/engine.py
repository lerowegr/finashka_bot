from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import DATA_DIR, settings

DATA_DIR.mkdir(exist_ok=True)

engine = create_async_engine(settings.db_url, echo=False)

if engine.url.get_backend_name() == "sqlite":

    @event.listens_for(engine.sync_engine, "connect")
    def _sqlite_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        # WAL: ETL пишет, бот читает — без взаимных блокировок
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_schema() -> None:
    from app.db import models

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)
