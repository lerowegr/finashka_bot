"""Оффлайн-проверка бота: сборка без токена и рендер карточек из локальной БД."""

from sqlalchemy import select

from app.bot import keyboards as kb
from app.bot import texts
from app.bot.main import build_dispatcher
from app.db import models as m
from app.db.engine import session_factory
from app.domain.services import catalog, search, universities


def test_dispatcher_builds_without_token():
    dp = build_dispatcher()
    # все семь роутеров подключены
    assert len(dp.sub_routers) == 7


def test_static_keyboards_build():
    assert kb.main_menu_kb().inline_keyboard
    assert kb.levels_kb().inline_keyboard


async def test_render_cards_from_local_db():
    """Карточки собираются из наполненной ETL-ом БД без обращения к сайту."""
    async with session_factory() as session:
        vuz = (await session.execute(select(m.University).limit(1))).scalar_one_or_none()
        if vuz is not None:
            full = await universities.university_by_id(session, vuz.id)
            assert vuz.short_name in texts.university_card(full)

        program = (await session.execute(select(m.Program).limit(1))).scalar_one_or_none()
        if program is not None:
            full = await search.program_by_id(session, program.id)
            assert "tabiturient.ru" in texts.program_card(full)

        direction = (
            await session.execute(select(m.Direction).where(m.Direction.is_active).limit(1))
        ).scalar_one_or_none()
        if direction is not None:
            count = await catalog.direction_programs_count(session, direction.id)
            assert direction.name in texts.direction_card(direction, count)
