from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot import texts
from app.bot.callbacks import MenuCb, RegionCb, RegionsCb, VuzCb, VuzDirCb, VuzDirsCb
from app.bot.keyboards import REGIONS_PER_PAGE
from app.domain.services import catalog, favorites, universities

router = Router(name="universities")


async def _render_regions(callback: CallbackQuery, session: AsyncSession, page: int) -> None:
    regions = await universities.regions(session)
    total = len(regions)
    start = page * REGIONS_PER_PAGE
    page_items = regions[start : start + REGIONS_PER_PAGE]
    if not page_items:
        await callback.answer("Нет данных о регионах", show_alert=True)
        return
    await callback.message.edit_text(
        "Выберите регион:", reply_markup=kb.regions_kb(page_items, page, total, REGIONS_PER_PAGE)
    )
    await callback.answer()


@router.callback_query(MenuCb.filter(F.to == "regions"))
async def show_regions(callback: CallbackQuery, session: AsyncSession) -> None:
    await _render_regions(callback, session, 0)


@router.callback_query(RegionsCb.filter())
async def paginate_regions(callback: CallbackQuery, callback_data: RegionsCb, session: AsyncSession) -> None:
    await _render_regions(callback, session, callback_data.page)


@router.callback_query(RegionCb.filter())
async def show_region_vuzes(callback: CallbackQuery, callback_data: RegionCb, session: AsyncSession) -> None:
    items, total = await universities.universities_page(
        session, callback_data.region_id, callback_data.page
    )
    if not items and callback_data.page == 0:
        await callback.answer("В этом регионе пока нет вузов", show_alert=True)
        return
    await callback.message.edit_text(
        "Выберите вуз:",
        reply_markup=kb.universities_kb(items, callback_data.page, total, callback_data.region_id),
    )
    await callback.answer()


@router.callback_query(VuzCb.filter())
async def show_vuz(callback: CallbackQuery, callback_data: VuzCb, session: AsyncSession) -> None:
    university = await universities.university_by_id(session, callback_data.univ_id)
    if university is None:
        await callback.answer("Вуз не найден", show_alert=True)
        return
    is_fav = await favorites.is_favorite(session, callback.from_user.id, "university", university.id)
    await callback.message.edit_text(
        texts.university_card(university), reply_markup=kb.university_card_kb(university, is_fav)
    )
    await callback.answer()


@router.callback_query(VuzDirsCb.filter())
async def show_vuz_directions(callback: CallbackQuery, callback_data: VuzDirsCb, session: AsyncSession) -> None:
    items, total = await universities.university_directions_page(
        session, callback_data.univ_id, callback_data.page
    )
    if not items and callback_data.page == 0:
        await callback.answer("У вуза пока нет направлений в базе", show_alert=True)
        return
    await callback.message.edit_text(
        "🎓 Направления вуза (нажмите — покажу профили):",
        reply_markup=kb.vuz_directions_kb(items, callback_data.page, total, callback_data.univ_id),
    )
    await callback.answer()


@router.callback_query(VuzDirCb.filter())
async def show_vuz_direction_profiles(callback: CallbackQuery, callback_data: VuzDirCb, session: AsyncSession) -> None:
    programs = await universities.vuz_direction_programs(
        session, callback_data.univ_id, callback_data.dir_id
    )
    if not programs:
        await callback.answer(
            "Профили этого направления пока не загружены", show_alert=True
        )
        return
    direction = await catalog.direction_by_id(session, callback_data.dir_id)
    header = (
        f"🎓 <b>{direction.name}</b> ({direction.code})\nПрофили в этом вузе:"
        if direction
        else "Профили:"
    )
    await callback.message.edit_text(
        header,
        reply_markup=kb.vuz_direction_profiles_kb(programs, callback_data.univ_id),
    )
    await callback.answer()
