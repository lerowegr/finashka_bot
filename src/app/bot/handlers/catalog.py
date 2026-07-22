from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot import texts
from app.bot.callbacks import (
    DirCb,
    DirProgsCb,
    EgeSearchCb,
    LevelCb,
    MenuCb,
    ProgCb,
    SectionCb,
    UgsnCb,
)
from app.domain.services import catalog, favorites, profile, search

router = Router(name="catalog")


@router.callback_query(MenuCb.filter(F.to == "catalog"))
async def show_levels(callback: CallbackQuery) -> None:
    await callback.message.edit_text("Выберите уровень образования:", reply_markup=kb.levels_kb())
    await callback.answer()


@router.callback_query(LevelCb.filter())
async def show_sections(callback: CallbackQuery, callback_data: LevelCb, session: AsyncSession) -> None:
    sections = await catalog.sections(session, callback_data.level)
    await callback.message.edit_text(
        "Выберите раздел наук:", reply_markup=kb.sections_kb(callback_data.level, sections)
    )
    await callback.answer()


@router.callback_query(SectionCb.filter())
async def show_ugsns(callback: CallbackQuery, callback_data: SectionCb, session: AsyncSession) -> None:
    ugsns = await catalog.ugsns(session, callback_data.level, callback_data.section_id)
    await callback.message.edit_text(
        "Выберите укрупнённую группу:",
        reply_markup=kb.ugsns_kb(callback_data.level, callback_data.section_id, ugsns),
    )
    await callback.answer()


@router.callback_query(UgsnCb.filter())
async def show_directions(callback: CallbackQuery, callback_data: UgsnCb, session: AsyncSession) -> None:
    directions = await catalog.directions(session, callback_data.level, callback_data.ugsn)
    await callback.message.edit_text(
        "Выберите направление:",
        reply_markup=kb.directions_kb(callback_data.level, callback_data.section_id, directions),
    )
    await callback.answer()


def _direction_back_cb(direction) -> UgsnCb:
    return UgsnCb(
        level=direction.level,
        section_id=direction.ugsn.section_id or 0,
        ugsn=direction.ugsn_code,
    )


@router.callback_query(DirCb.filter())
async def show_direction(callback: CallbackQuery, callback_data: DirCb, session: AsyncSession) -> None:
    direction = await catalog.direction_by_id(session, callback_data.dir_id)
    if direction is None:
        await callback.answer("Направление не найдено, обновите меню", show_alert=True)
        return
    count = await catalog.direction_programs_count(session, direction.id)
    is_fav = await favorites.is_favorite(session, callback.from_user.id, "direction", direction.id)
    await callback.message.edit_text(
        texts.direction_card(direction, count),
        reply_markup=kb.direction_card_kb(direction, is_fav, count > 0, _direction_back_cb(direction)),
    )
    await callback.answer()


@router.callback_query(DirProgsCb.filter())
async def show_direction_programs(
    callback: CallbackQuery, callback_data: DirProgsCb, session: AsyncSession, state: FSMContext
) -> None:
    subject_ids = None
    if callback_data.ege:
        data = await state.get_data()
        subject_ids = set(data.get("subjects", [])) or None

    items, total = await search.programs_by_direction_and_subjects(
        session, callback_data.dir_id, subject_ids, callback_data.page
    )
    if not items and callback_data.page == 0:
        await callback.answer("Нет программ по этому направлению", show_alert=True)
        return

    scores = await profile.get_scores(session, callback.from_user.id)

    def label(program) -> str:
        prefix = profile.status_prefix(profile.evaluate(program, scores)[0]) if scores else ""
        score = next((f" · {f.pass_score}" for f in program.forms if f.pass_score), "")
        return f"{prefix}{program.university.short_name}{score}"

    def page_cb(page: int) -> DirProgsCb:
        return DirProgsCb(dir_id=callback_data.dir_id, page=page, ege=callback_data.ege)

    back = EgeSearchCb(page=0) if callback_data.ege else DirCb(dir_id=callback_data.dir_id)
    direction = await catalog.direction_by_id(session, callback_data.dir_id)
    header = (
        f"🏛 Вузы с направлением <b>{direction.name}</b> ({direction.code}):"
        if direction
        else "Программы:"
    )
    await callback.message.edit_text(
        header, reply_markup=kb.programs_list_kb(items, callback_data.page, total, page_cb, back, label)
    )
    await callback.answer()


@router.callback_query(ProgCb.filter())
async def show_program(callback: CallbackQuery, callback_data: ProgCb, session: AsyncSession) -> None:
    program = await search.program_by_id(session, callback_data.prog_id)
    if program is None:
        await callback.answer("Программа не найдена", show_alert=True)
        return
    is_fav = await favorites.is_favorite(session, callback.from_user.id, "program", program.id)
    scores = await profile.get_scores(session, callback.from_user.id)
    chance = profile.evaluate(program, scores) if scores else None
    await callback.message.edit_text(
        texts.program_card(program, chance), reply_markup=kb.program_card_kb(program, is_fav)
    )
    await callback.answer()
