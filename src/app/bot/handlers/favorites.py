from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import FavToggleCb, MenuCb, UgsnCb
from app.domain.services import catalog, favorites, search, universities

router = Router(name="favorites")


@router.callback_query(MenuCb.filter(F.to == "favs"))
async def show_favorites(callback: CallbackQuery, session: AsyncSession) -> None:
    grouped = await favorites.list_all(session, callback.from_user.id)
    if any(grouped.values()):
        text = "⭐ Ваше избранное:"
    else:
        text = "У вас пока нет избранного.\nДобавляйте направления, вузы и программы кнопкой ☆."
    await callback.message.edit_text(text, reply_markup=kb.favorites_kb(grouped))
    await callback.answer()


@router.callback_query(FavToggleCb.filter())
async def toggle_favorite(callback: CallbackQuery, callback_data: FavToggleCb, session: AsyncSession) -> None:
    now_fav = await favorites.toggle(
        session, callback.from_user.id, callback_data.kind, callback_data.item_id
    )
    await callback.answer("Добавлено в избранное ⭐" if now_fav else "Убрано из избранного")

    # обновляем только кнопку избранного на текущей карточке
    try:
        if callback_data.kind == "direction":
            direction = await catalog.direction_by_id(session, callback_data.item_id)
            if direction is None:
                return
            count = await catalog.direction_programs_count(session, direction.id)
            back = UgsnCb(
                level=direction.level,
                section_id=direction.ugsn.section_id or 0,
                ugsn=direction.ugsn_code,
            )
            markup = kb.direction_card_kb(direction, now_fav, count > 0, back)
        elif callback_data.kind == "university":
            university = await universities.university_by_id(session, callback_data.item_id)
            if university is None:
                return
            markup = kb.university_card_kb(university, now_fav)
        else:
            program = await search.program_by_id(session, callback_data.item_id)
            if program is None:
                return
            markup = kb.program_card_kb(program, now_fav)
        await callback.message.edit_reply_markup(reply_markup=markup)
    except TelegramBadRequest:
        pass
