from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot.callbacks import EgePickerCb, EgeSearchCb, MenuCb, SubjToggleCb
from app.domain.services import profile, search

router = Router(name="ege")

_PICKER_TEXT = "Отметьте предметы ЕГЭ, которые сдаёте, и нажмите «Искать»:"


class EgeStates(StatesGroup):
    choosing = State()


async def _render_picker(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    selected = set(data.get("subjects", []))
    subjects = await search.all_subjects(session)
    await callback.message.edit_text(_PICKER_TEXT, reply_markup=kb.subjects_kb(subjects, selected))


@router.callback_query(MenuCb.filter(F.to == "ege"))
async def open_ege(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.set_state(EgeStates.choosing)
    # предзаполняем набор предметами из профиля «Мои баллы», если он есть
    saved = await profile.get_scores(session, callback.from_user.id)
    await state.update_data(subjects=list(saved.keys()))
    await _render_picker(callback, session, state)
    await callback.answer()


@router.callback_query(EgePickerCb.filter())
async def back_to_picker(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await _render_picker(callback, session, state)
    await callback.answer()


@router.callback_query(SubjToggleCb.filter())
async def toggle_subject(
    callback: CallbackQuery, callback_data: SubjToggleCb, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    selected = set(data.get("subjects", []))
    selected ^= {callback_data.subject_id}
    await state.update_data(subjects=list(selected))
    subjects = await search.all_subjects(session)
    await callback.message.edit_reply_markup(reply_markup=kb.subjects_kb(subjects, selected))
    await callback.answer()


@router.callback_query(EgeSearchCb.filter())
async def search_directions(
    callback: CallbackQuery, callback_data: EgeSearchCb, session: AsyncSession, state: FSMContext
) -> None:
    data = await state.get_data()
    selected = set(data.get("subjects", []))
    if not selected:
        await callback.answer("Отметьте хотя бы один предмет", show_alert=True)
        return
    results, total = await search.directions_by_subjects(session, selected, callback_data.page)
    if not results:
        await callback.answer("Нет направлений под этот набор предметов", show_alert=True)
        return
    await callback.message.edit_text(
        "Направления, доступные с вашим набором ЕГЭ:",
        reply_markup=kb.ege_results_kb(results, callback_data.page, total),
    )
    await callback.answer()
