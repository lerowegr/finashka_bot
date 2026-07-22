"""Поиск по предметам ЕГЭ.

Программа подходит, если все её обязательные предметы входят в набор пользователя
и хотя бы один предмет «на выбор» тоже в наборе (когда выбор есть).
"""

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import models as m


async def all_subjects(session: AsyncSession) -> list[m.ExamSubject]:
    return (
        (await session.execute(select(m.ExamSubject).order_by(m.ExamSubject.id))).scalars().all()
    )


def _fit_condition(subject_ids: set[int]):
    pe = m.ProgramExam
    has_any_exam = exists().where(pe.program_id == m.Program.id)
    no_unmet_required = ~exists().where(
        pe.program_id == m.Program.id,
        pe.kind == "required",
        pe.subject_id.not_in(subject_ids),
    )
    no_choice = ~exists().where(pe.program_id == m.Program.id, pe.kind == "choice")
    choice_met = exists().where(
        pe.program_id == m.Program.id,
        pe.kind == "choice",
        pe.subject_id.in_(subject_ids),
    )
    return has_any_exam & no_unmet_required & (no_choice | choice_met)


async def directions_by_subjects(
    session: AsyncSession, subject_ids: set[int], page: int, per_page: int = 8
) -> tuple[list[tuple[m.Direction, int]], int]:
    """Направления с числом подходящих программ."""
    base = (
        select(m.Direction, func.count(m.Program.id).label("cnt"))
        .join(m.Program, m.Program.direction_id == m.Direction.id)
        .where(m.Program.is_active, _fit_condition(subject_ids))
        .group_by(m.Direction.id)
    )
    total = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    rows = (
        await session.execute(
            base.order_by(func.count(m.Program.id).desc(), m.Direction.code)
            .offset(page * per_page)
            .limit(per_page)
        )
    ).all()
    return [(row[0], row[1]) for row in rows], total


async def programs_by_direction_and_subjects(
    session: AsyncSession,
    direction_id: int,
    subject_ids: set[int] | None,
    page: int,
    per_page: int = 8,
) -> tuple[list[m.Program], int]:
    base = select(m.Program).where(
        m.Program.direction_id == direction_id, m.Program.is_active
    )
    if subject_ids:
        base = base.where(_fit_condition(subject_ids))
    total = (
        await session.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    items = (
        (
            await session.execute(
                base.options(selectinload(m.Program.forms), selectinload(m.Program.exams))
                .join(m.University, m.Program.university_id == m.University.id)
                .order_by(m.University.avg_score.desc().nulls_last())
                .offset(page * per_page)
                .limit(per_page)
            )
        )
        .scalars()
        .all()
    )
    return items, total


async def program_by_id(session: AsyncSession, program_id: int) -> m.Program | None:
    return (
        await session.execute(
            select(m.Program)
            .options(selectinload(m.Program.forms), selectinload(m.Program.exams))
            .where(m.Program.id == program_id)
        )
    ).scalar_one_or_none()
