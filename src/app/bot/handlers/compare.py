from aiogram import Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot import texts
from app.bot.callbacks import CompareCb, CompareStartCb
from app.domain.services import compare, favorites

router = Router(name="compare")


@router.callback_query(CompareStartCb.filter())
async def choose_second(callback: CallbackQuery, callback_data: CompareStartCb, session: AsyncSession) -> None:
    grouped = await favorites.list_all(session, callback.from_user.id)
    candidates = [u for u in grouped["university"] if u.id != callback_data.a]
    if not candidates:
        await callback.answer(
            "Добавьте другие вузы в избранное (☆), чтобы сравнить с ними", show_alert=True
        )
        return
    await callback.message.edit_text(
        "С каким вузом сравнить? Выберите из избранного:",
        reply_markup=kb.compare_candidates_kb(callback_data.a, candidates),
    )
    await callback.answer()


@router.callback_query(CompareCb.filter())
async def show_comparison(callback: CallbackQuery, callback_data: CompareCb, session: AsyncSession) -> None:
    result = await compare.compare(session, callback_data.a, callback_data.b)
    if result is None:
        await callback.answer("Один из вузов не найден, обновите меню", show_alert=True)
        return
    a, b, rows = result
    await callback.message.edit_text(
        texts.comparison_text(a, b, rows),
        reply_markup=kb.compare_result_kb(callback_data.a, callback_data.b),
    )
    await callback.answer()
