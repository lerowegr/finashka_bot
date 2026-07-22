"""Уведомления об изменениях в избранном — на изолированной in-memory БД."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db import models as m
from app.domain.services import notifications


@pytest_asyncio.fixture
async def session():
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as conn:
        await conn.run_sync(m.Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        yield s
    await engine.dispose()


async def _seed(s):
    s.add(m.Ugsn(code="38.00.00", name="Экономика и управление"))
    s.add(
        m.Direction(id=1, code="38.03.01", name="Экономика", level="bachelor", ugsn_code="38.00.00")
    )
    s.add(m.University(id=1, slug="fu", short_name="ФУ", full_name="Финансовый университет"))
    s.add(m.Program(id=100, university_id=1, direction_id=1, profile="Финансы"))
    s.add(m.User(tg_id=555))
    s.add(m.Favorite(tg_id=555, kind="program", item_id=100))
    s.add(m.ScrapeRun(id=7, kind="light"))
    await s.flush()


async def test_collect_and_format(session):
    await _seed(session)
    session.add(
        m.ChangeLog(entity="program_form", entity_id=100, field="pass_score",
                    old_value="231", new_value="236", scrape_run_id=7)
    )
    session.add(
        m.ChangeLog(entity="program_form", entity_id=100, field="tuition",
                    old_value="350000", new_value="360000", scrape_run_id=7)
    )
    # изменение по НЕизбранной программе — не должно попасть
    session.add(
        m.ChangeLog(entity="program_form", entity_id=999, field="pass_score",
                    old_value="100", new_value="110", scrape_run_id=7)
    )
    await session.commit()

    grouped = await notifications.collect_favorite_program_changes(session, [7])
    assert set(grouped) == {555}
    assert len(grouped[555]) == 2

    message = notifications.format_changes_message(grouped[555])
    assert "Экономика" in message and "ФУ" in message
    assert "231" in message and "236" in message
    assert "проходной балл" in message
    assert "стоимость обучения" in message and "₽" in message


async def test_no_changes_returns_empty(session):
    await _seed(session)
    await session.commit()
    assert await notifications.collect_favorite_program_changes(session, [7]) == {}


async def test_empty_run_ids(session):
    assert await notifications.collect_favorite_program_changes(session, []) == {}
