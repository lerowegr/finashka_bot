"""Сравнение вузов — на изолированной in-memory БД."""

import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.bot import texts
from app.db import models as m
from app.domain.services import compare


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
    s.add(m.Ugsn(code="01.00.00", name="Математика"))
    s.add(m.Direction(id=1, code="01.03.01", name="Математика", level="bachelor", ugsn_code="01.00.00"))
    s.add(m.Direction(id=2, code="01.03.02", name="ПМИ", level="bachelor", ugsn_code="01.00.00"))
    # вуз A: балл выше, категория A, общежитие есть, военный центр есть, 2 направления
    s.add(m.University(id=1, slug="a", short_name="ВУЗ-А", full_name="Вуз А",
                       avg_score=85.0, budget_seats=1000, category="A", dorm="yes", military_center=True))
    # вуз B: балл ниже, категория C, общежития нет, военного центра нет, 1 направление
    s.add(m.University(id=2, slug="b", short_name="ВУЗ-Б", full_name="Вуз Б",
                       avg_score=70.0, budget_seats=1500, category="C", dorm="no", military_center=False))
    s.add(m.Program(id=10, university_id=1, direction_id=1))
    s.add(m.Program(id=11, university_id=1, direction_id=2))
    s.add(m.Program(id=20, university_id=2, direction_id=1))
    await s.flush()


def _row(rows, label):
    return next(r for r in rows if r["label"] == label)


async def test_compare_metrics(session):
    await _seed(session)
    await session.commit()

    result = await compare.compare(session, 1, 2)
    assert result is not None
    a, b, rows = result
    assert (a.id, b.id) == (1, 2)

    assert _row(rows, "Средний балл")["better"] == "a"       # 85 > 70
    assert _row(rows, "Бюджетных мест")["better"] == "b"     # 1500 > 1000
    assert _row(rows, "Направлений")["a"] == "2" and _row(rows, "Направлений")["better"] == "a"
    assert _row(rows, "Программ")["a"] == "2" and _row(rows, "Программ")["b"] == "1"
    assert _row(rows, "Категория")["better"] == "a"          # A лучше C
    assert _row(rows, "Общежитие")["better"] == "a"          # есть лучше нет
    assert _row(rows, "Военный центр")["better"] == "a"

    # рендер не падает и помечает победителя галочкой
    rendered = texts.comparison_text(a, b, rows)
    assert "ВУЗ-А" in rendered and "ВУЗ-Б" in rendered
    assert "✅" in rendered


async def test_category_modifier_ranks_above_lower_letter(session):
    # регресс: 'B-' должен быть лучше 'C' (раньше проваливался в ранг 0)
    s = session
    s.add(m.University(id=1, slug="a", short_name="A", full_name="A", category="C"))
    s.add(m.University(id=2, slug="b", short_name="B", full_name="B", category="B-"))
    await s.commit()
    _, _, rows = await compare.compare(s, 1, 2)
    assert _row(rows, "Категория")["better"] == "b"


async def test_compare_missing_university(session):
    await _seed(session)
    await session.commit()
    assert await compare.compare(session, 1, 999) is None
