"""Каталог: уровень -> раздел наук -> УГСН -> направление. Без aiogram и httpx."""

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m

OTHER_SECTION_ID = 0  # для УГСН, не попавших в seed-разделы


def _active_directions(level: str) -> Select:
    return select(m.Direction).where(m.Direction.level == level, m.Direction.is_active)


async def sections(session: AsyncSession, level: str) -> list[tuple[int, str, int]]:
    """[(section_id, name, directions_count)] для уровня образования."""
    rows = (
        await session.execute(
            select(
                func.coalesce(m.Section.id, OTHER_SECTION_ID),
                func.coalesce(m.Section.name, "Прочее"),
                func.count(m.Direction.id),
            )
            .select_from(m.Direction)
            .join(m.Ugsn, m.Direction.ugsn_code == m.Ugsn.code)
            .outerjoin(m.Section, m.Ugsn.section_id == m.Section.id)
            .where(m.Direction.level == level, m.Direction.is_active)
            .group_by(m.Section.id, m.Section.name)
            .order_by(func.coalesce(m.Section.id, OTHER_SECTION_ID))
        )
    ).all()
    return [tuple(r) for r in rows]


async def ugsns(session: AsyncSession, level: str, section_id: int) -> list[tuple[str, str, int]]:
    """[(ugsn_code, name, directions_count)] раздела."""
    section_filter = (
        m.Ugsn.section_id.is_(None) if section_id == OTHER_SECTION_ID
        else m.Ugsn.section_id == section_id
    )
    rows = (
        await session.execute(
            select(m.Ugsn.code, m.Ugsn.name, func.count(m.Direction.id))
            .join(m.Direction, m.Direction.ugsn_code == m.Ugsn.code)
            .where(m.Direction.level == level, m.Direction.is_active, section_filter)
            .group_by(m.Ugsn.code, m.Ugsn.name)
            .order_by(m.Ugsn.code)
        )
    ).all()
    return [tuple(r) for r in rows]


async def directions(session: AsyncSession, level: str, ugsn_code: str) -> list[m.Direction]:
    return (
        (
            await session.execute(
                _active_directions(level)
                .where(m.Direction.ugsn_code == ugsn_code)
                .order_by(m.Direction.code)
            )
        )
        .scalars()
        .all()
    )


async def direction_by_id(session: AsyncSession, direction_id: int) -> m.Direction | None:
    return await session.get(m.Direction, direction_id)


async def direction_programs_count(session: AsyncSession, direction_id: int) -> int:
    return (
        await session.execute(
            select(func.count())
            .select_from(m.Program)
            .where(m.Program.direction_id == direction_id, m.Program.is_active)
        )
    ).scalar_one()
