from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import models as m


async def regions(session: AsyncSession) -> list[tuple[int, str, int]]:
    """[(region_id, name, vuz_count)], по убыванию числа вузов."""
    rows = (
        await session.execute(
            select(m.Region.id, m.Region.name, func.count(m.University.id))
            .join(m.University, m.University.region_id == m.Region.id)
            .where(m.University.is_active)
            .group_by(m.Region.id, m.Region.name)
            .order_by(func.count(m.University.id).desc(), m.Region.name)
        )
    ).all()
    return [tuple(r) for r in rows]


async def universities_page(
    session: AsyncSession, region_id: int, page: int, per_page: int = 8
) -> tuple[list[m.University], int]:
    base = select(m.University).where(
        m.University.region_id == region_id, m.University.is_active
    )
    total = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    items = (
        (
            await session.execute(
                base.order_by(m.University.avg_score.desc().nulls_last(), m.University.short_name)
                .offset(page * per_page)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )
    return items, total


async def university_by_id(session: AsyncSession, univ_id: int) -> m.University | None:
    return (
        await session.execute(
            select(m.University)
            .options(selectinload(m.University.faculties), selectinload(m.University.open_days))
            .where(m.University.id == univ_id)
        )
    ).scalar_one_or_none()


async def university_directions_page(
    session: AsyncSession, univ_id: int, page: int, per_page: int = 8
) -> tuple[list[tuple[m.Direction, int]], int]:
    """Направления вуза (каждое один раз) с числом профилей."""
    total = (
        await session.execute(
            select(func.count())
            .select_from(m.UniversityDirection)
            .where(m.UniversityDirection.university_id == univ_id)
        )
    ).scalar_one()

    profiles = (
        select(
            m.Program.direction_id.label("did"),
            func.count(m.Program.id).label("cnt"),
        )
        .where(m.Program.university_id == univ_id, m.Program.is_active)
        .group_by(m.Program.direction_id)
        .subquery()
    )
    rows = (
        await session.execute(
            select(m.Direction, func.coalesce(profiles.c.cnt, 0))
            .join(m.UniversityDirection, m.UniversityDirection.direction_id == m.Direction.id)
            .outerjoin(profiles, profiles.c.did == m.Direction.id)
            .where(m.UniversityDirection.university_id == univ_id)
            .order_by(m.Direction.code)
            .offset(page * per_page)
            .limit(per_page)
        )
    ).all()
    return [(direction, count) for direction, count in rows], total


async def vuz_direction_programs(
    session: AsyncSession, univ_id: int, direction_id: int
) -> list[m.Program]:
    """Профили одного направления в конкретном вузе."""
    return (
        (
            await session.execute(
                select(m.Program)
                .options(selectinload(m.Program.forms))
                .where(
                    m.Program.university_id == univ_id,
                    m.Program.direction_id == direction_id,
                    m.Program.is_active,
                )
                .order_by(m.Program.profile)
            )
        )
        .scalars()
        .all()
    )
