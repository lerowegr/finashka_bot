"""Сравнение двух вузов по ключевым метрикам. Данные уже в БД — парсер не нужен."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.domain.services.universities import university_by_id

DORM_RANK = {"yes": 3, "not_all": 2, "no": 1}
DORM_TEXT = {"yes": "есть", "not_all": "есть, не всем", "no": "нет"}
_BASE_CATEGORY = {"A": 4, "B": 3, "C": 2, "D": 1, "E": 1}


def _category_rank(category: str | None) -> float:
    """Категория вида 'A', 'B+', 'C-' — ранг по букве с поправкой на +/-."""
    if not category:
        return 0
    base = _BASE_CATEGORY.get(category[0].upper(), 0)
    if base == 0:
        return 0
    if category.endswith("+"):
        base += 0.3
    elif category.endswith("-"):
        base -= 0.3
    return base


async def _counts(session: AsyncSession, univ_id: int) -> tuple[int, int]:
    programs = (
        await session.execute(
            select(func.count())
            .select_from(m.Program)
            .where(m.Program.university_id == univ_id, m.Program.is_active)
        )
    ).scalar_one()
    directions = (
        await session.execute(
            select(func.count(func.distinct(m.Program.direction_id))).where(
                m.Program.university_id == univ_id, m.Program.is_active
            )
        )
    ).scalar_one()
    return directions, programs


def _better_numeric(a, b) -> str | None:
    if a is None and b is None:
        return None
    if b is None or (a is not None and a > b):
        return "a"
    if a is None or b > a:
        return "b"
    return None


def _rank_row(icon, label, a_val, b_val, rank_fn, fmt):
    ra, rb = rank_fn(a_val), rank_fn(b_val)
    better = "a" if ra > rb else "b" if rb > ra else None
    return {"icon": icon, "label": label, "a": fmt(a_val), "b": fmt(b_val), "better": better}


def _bool_row(icon, label, a_val, b_val):
    text = {True: "да", False: "нет", None: "нет данных"}
    better = "a" if a_val and not b_val else "b" if b_val and not a_val else None
    return {"icon": icon, "label": label, "a": text[a_val], "b": text[b_val], "better": better}


def _num_row(icon, label, a_val, b_val, fmt=str):
    return {
        "icon": icon,
        "label": label,
        "a": fmt(a_val) if a_val is not None else "—",
        "b": fmt(b_val) if b_val is not None else "—",
        "better": _better_numeric(a_val, b_val),
    }


async def compare(session: AsyncSession, a_id: int, b_id: int):
    """(vuz_a, vuz_b, rows) или None. rows: [{icon,label,a,b,better}], better in {'a','b',None}."""
    a = await university_by_id(session, a_id)
    b = await university_by_id(session, b_id)
    if a is None or b is None:
        return None

    a_dir, a_prog = await _counts(session, a_id)
    b_dir, b_prog = await _counts(session, b_id)

    rows = [
        _num_row("📊", "Средний балл", a.avg_score, b.avg_score, lambda x: f"{x:g}"),
        _num_row("🎓", "Бюджетных мест", a.budget_seats, b.budget_seats),
        _num_row("🧭", "Направлений", a_dir, b_dir),
        _num_row("📚", "Программ", a_prog, b_prog),
        _rank_row("🏆", "Категория", a.category, b.category, _category_rank, lambda x: x or "—"),
        _rank_row(
            "🏠", "Общежитие", a.dorm, b.dorm,
            lambda v: DORM_RANK.get(v, 0), lambda x: DORM_TEXT.get(x, "нет данных")
        ),
        _bool_row("🎖", "Военный центр", a.military_center, b.military_center),
    ]
    return a, b, rows
