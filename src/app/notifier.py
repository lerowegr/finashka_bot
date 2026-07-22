"""Рассылка уведомлений об изменениях в избранных программах после обхода."""

import logging

from app import notify
from app.db.engine import session_factory
from app.domain.services import notifications

log = logging.getLogger(__name__)


async def dispatch_change_notifications(run_ids: list[int]) -> int:
    """Разослать уведомления об изменениях за указанные обходы. Возвращает число адресатов."""
    run_ids = [r for r in run_ids if r]
    if not run_ids:
        return 0

    async with session_factory() as session:
        grouped = await notifications.collect_favorite_program_changes(session, run_ids)

    sent = 0
    for tg_id, items in grouped.items():
        text = notifications.format_changes_message(items)
        if await notify.send_message(tg_id, text):
            sent += 1
    log.info("уведомления об изменениях: адресатов %d из %d", sent, len(grouped))
    return sent
