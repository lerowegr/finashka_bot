from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m

KINDS = ("direction", "university", "program")


async def toggle(session: AsyncSession, tg_id: int, kind: str, item_id: int) -> bool:
    """Добавляет/убирает из избранного; возвращает новое состояние."""
    assert kind in KINDS
    favorite = await session.get(m.Favorite, (tg_id, kind, item_id))
    if favorite is not None:
        await session.delete(favorite)
        await session.commit()
        return False
    session.add(m.Favorite(tg_id=tg_id, kind=kind, item_id=item_id))
    await session.commit()
    return True


async def is_favorite(session: AsyncSession, tg_id: int, kind: str, item_id: int) -> bool:
    return await session.get(m.Favorite, (tg_id, kind, item_id)) is not None


async def list_all(session: AsyncSession, tg_id: int) -> dict[str, list]:
    """Избранное пользователя тремя типизированными списками."""
    favorites = (
        (
            await session.execute(
                select(m.Favorite)
                .where(m.Favorite.tg_id == tg_id)
                .order_by(m.Favorite.created_at)
            )
        )
        .scalars()
        .all()
    )
    result: dict[str, list] = {"direction": [], "university": [], "program": []}
    model_by_kind = {"direction": m.Direction, "university": m.University, "program": m.Program}
    for favorite in favorites:
        item = await session.get(model_by_kind[favorite.kind], favorite.item_id)
        if item is not None:
            result[favorite.kind].append(item)
    return result
