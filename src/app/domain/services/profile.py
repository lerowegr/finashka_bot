"""Профиль «Мои баллы ЕГЭ» и оценка шансов поступления.

Логика чистая (без Telegram): те же функции переиспользует будущий Mini App API.
"""

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m

# Статусы шанса и их отображение
STATUS_EMOJI = {"pass": "🟢", "edge": "🟡", "low": "🔴", "missing": "⚪", "unknown": ""}
STATUS_WORD = {
    "pass": "проходите с запасом",
    "edge": "на грани",
    "low": "баллов не хватает",
    "missing": "не хватает предмета",
    "unknown": "",
}

# Пороги относительно прошлогоднего проходного балла
MARGIN_SAFE = 10  # >= проходной + 10 -> уверенно
MARGIN_EDGE = 5  # >= проходной - 5 -> на грани


async def get_scores(session: AsyncSession, tg_id: int) -> dict[int, int]:
    rows = (
        (await session.execute(select(m.UserScore).where(m.UserScore.tg_id == tg_id)))
        .scalars()
        .all()
    )
    return {r.subject_id: r.score for r in rows}


async def scores_overview(session: AsyncSession, tg_id: int) -> list[tuple[m.ExamSubject, int | None]]:
    """Все предметы с текущим баллом (или None) — для экрана профиля."""
    subjects = (
        (await session.execute(select(m.ExamSubject).order_by(m.ExamSubject.id))).scalars().all()
    )
    scores = await get_scores(session, tg_id)
    return [(s, scores.get(s.id)) for s in subjects]


async def set_score(session: AsyncSession, tg_id: int, subject_id: int, score: int) -> None:
    row = await session.get(m.UserScore, (tg_id, subject_id))
    if row is None:
        session.add(m.UserScore(tg_id=tg_id, subject_id=subject_id, score=score))
    else:
        row.score = score
    await session.commit()


async def clear_scores(session: AsyncSession, tg_id: int) -> None:
    await session.execute(delete(m.UserScore).where(m.UserScore.tg_id == tg_id))
    await session.commit()


def _program_pass_score(program, form: str = "full") -> tuple[int | None, int | None]:
    """Проходной балл нужной формы (или любой доступной) + год."""
    for f in program.forms:
        if f.form == form and f.pass_score:
            return f.pass_score, f.pass_score_year
    for f in program.forms:
        if f.pass_score:
            return f.pass_score, f.pass_score_year
    return None, None


def _user_total(program, scores: dict[int, int]) -> tuple[int | None, bool]:
    """Сумма баллов пользователя под набор экзаменов программы.

    Возвращает (сумма, не_хватает_предмета). Сумма None, если для расчёта не хватает
    обязательного предмета или ни одного предмета «на выбор».
    """
    required = [e.subject_id for e in program.exams if e.kind == "required"]
    choice = [e.subject_id for e in program.exams if e.kind == "choice"]
    if not required and not choice:
        return None, False  # набор экзаменов неизвестен

    if any(s not in scores for s in required):
        return None, True
    total = sum(scores[s] for s in required)

    if choice:
        available = [scores[s] for s in choice if s in scores]
        if not available:
            return None, True
        total += max(available)
    return total, False


def evaluate(program, scores: dict[int, int]) -> tuple[str, int | None, int | None]:
    """(status, сумма_пользователя, проходной_балл). status: pass|edge|low|missing|unknown."""
    if not scores:
        return "unknown", None, None
    total, missing = _user_total(program, scores)
    pass_score, _year = _program_pass_score(program)
    if missing:
        return "missing", None, pass_score
    if total is None or pass_score is None:
        return "unknown", total, pass_score
    if total >= pass_score + MARGIN_SAFE:
        return "pass", total, pass_score
    if total >= pass_score - MARGIN_EDGE:
        return "edge", total, pass_score
    return "low", total, pass_score


def status_prefix(status: str) -> str:
    """Эмодзи-префикс для кнопки в списке программ ('' если статус неизвестен)."""
    emoji = STATUS_EMOJI.get(status, "")
    return f"{emoji} " if emoji else ""
