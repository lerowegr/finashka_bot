import asyncio
from pathlib import Path

import typer

from app.config import BASE_DIR
from app.logsetup import setup_logging

app = typer.Typer(help="Финашка-бот: управление данными и обходами tabiturient.ru")
etl_app = typer.Typer(help="Обходы tabiturient.ru")
app.add_typer(etl_app, name="etl")

OLD_BOT_DIR = BASE_DIR.parent / "finashka_bot-main"


def _run(coro) -> None:
    setup_logging("etl")
    asyncio.run(coro)


@app.command()
def db_init() -> None:
    """Создать схему БД."""
    from app.db.engine import create_schema

    _run(create_schema())
    typer.echo("Схема БД создана")


@app.command()
def seed_extract(old: Path = typer.Option(OLD_BOT_DIR, help="Папка старого бота с Excel")) -> None:
    """Извлечь авторские данные из старых Excel в data/seed/."""
    from app.seed import extract_from_excel

    setup_logging("etl")
    extract_from_excel(old)


@app.command()
def seed_apply() -> None:
    """Наложить seed (описания, военные кафедры) на наполненную БД."""
    from app.seed import apply_seed

    _run(apply_seed())


@app.command()
def migrate_favorites(
    old_db: Path = typer.Option(OLD_BOT_DIR / "data.db", help="SQLite старого бота")
) -> None:
    """Перенести избранное пользователей из старого бота."""
    from app.seed import migrate_favorites as _migrate

    _run(_migrate(old_db))


@etl_app.command("light")
def etl_light(limit: int | None = typer.Option(None, help="Обойти только N вузов")) -> None:
    """Вузы + списки программ (~3 запроса на вуз, ~40 мин на все)."""
    from app.scraper.etl import Etl

    _run(Etl().run_light(limit_vuz=limit))


@etl_app.command("np")
def etl_np(limit: int | None = typer.Option(None)) -> None:
    """Агрегаты направлений (~5 мин)."""
    from app.scraper.etl import Etl

    _run(Etl().run_np(limit=limit))


@etl_app.command("full")
def etl_full(limit: int | None = typer.Option(None, help="Обойти только N карточек")) -> None:
    """Карточки программ: стоимость, места (~7 часов на все, гонять ночью)."""
    from app.scraper.etl import Etl

    _run(Etl().run_full(limit=limit))


@app.command()
def schedule() -> None:
    """Планировщик обновления БД.

    Каждую ночь (03:00): лёгкий обход вузов + агрегаты направлений (~45 мин) —
    свежие баллы, ЕГЭ и новые программы. Раз в неделю ночью (вс 01:00): полные
    карточки программ (стоимость, места, квоты) — эти данные меняются редко.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    from app.scraper.etl import Etl

    async def nightly(etl: Etl) -> None:
        await etl.run_light()
        await etl.run_np()

    async def main() -> None:
        etl = Etl()
        scheduler = AsyncIOScheduler()
        scheduler.add_job(nightly, "cron", hour=3, minute=0, args=[etl])
        scheduler.add_job(etl.run_full, "cron", day_of_week="sun", hour=1, minute=0)
        scheduler.start()
        await asyncio.Event().wait()  # работает, пока не остановят

    _run(main())


@app.command()
def stats() -> None:
    """Сводка по данным в БД."""
    from sqlalchemy import func, select

    from app.db import models as m
    from app.db.engine import session_factory

    async def main() -> None:
        async with session_factory() as session:
            for model in (m.Region, m.University, m.Direction, m.Program, m.ProgramForm,
                          m.ExamSubject, m.User, m.Favorite, m.ScrapeRun):
                count = (await session.execute(select(func.count()).select_from(model))).scalar()
                typer.echo(f"{model.__tablename__:15} {count}")

    _run(main())


if __name__ == "__main__":
    app()
