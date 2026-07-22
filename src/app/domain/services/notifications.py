"""Сопоставление изменений (change_log) с избранным пользователей.

Логика чистая: собирает и форматирует данные, отправку делает слой notify.
"""

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m

FIELD_RU = {"pass_score": "проходной балл", "tuition": "стоимость обучения"}
TRACKED_FIELDS = list(FIELD_RU)


async def collect_favorite_program_changes(
    session: AsyncSession, run_ids: list[int]
) -> dict[int, list[dict]]:
    """{tg_id: [{program, field, old, new}]} — изменения в избранных программах за обход(ы)."""
    run_ids = [r for r in run_ids if r]
    if not run_ids:
        return {}

    rows = (
        await session.execute(
            select(m.ChangeLog, m.Favorite.tg_id, m.Program)
            .join(
                m.Favorite,
                and_(
                    m.Favorite.kind == "program",
                    m.Favorite.item_id == m.ChangeLog.entity_id,
                ),
            )
            .join(m.Program, m.Program.id == m.ChangeLog.entity_id)
            .where(
                m.ChangeLog.scrape_run_id.in_(run_ids),
                m.ChangeLog.entity == "program_form",
                m.ChangeLog.field.in_(TRACKED_FIELDS),
            )
            .order_by(m.Favorite.tg_id)
        )
    ).all()

    grouped: dict[int, list[dict]] = {}
    for change, tg_id, program in rows:
        grouped.setdefault(tg_id, []).append(
            {
                "program": program,
                "field": change.field,
                "old": change.old_value,
                "new": change.new_value,
            }
        )
    return grouped


def format_changes_message(items: list[dict]) -> str:
    """Одно сообщение пользователю: изменения, сгруппированные по программе."""
    programs: dict[int, m.Program] = {}
    by_program: dict[int, list[dict]] = {}
    for item in items:
        pid = item["program"].id
        programs[pid] = item["program"]
        by_program.setdefault(pid, []).append(item)

    lines = ["🔔 <b>Изменения в ваших избранных программах</b>"]
    for pid, changes in by_program.items():
        program = programs[pid]
        lines.append(f"\n📚 {program.direction.name} — {program.university.short_name}")
        for item in changes:
            field = FIELD_RU.get(item["field"], item["field"])
            suffix = " ₽" if item["field"] == "tuition" else ""
            lines.append(f" • {field}: {item['old']}{suffix} → {item['new']}{suffix}")
    return "\n".join(lines)
