from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot import keyboards as kb
from app.bot import texts
from app.bot.callbacks import MenuCb, ProfileCb, ScoreSubjCb
from app.db import models as m
from app.domain.services import profile

router = Router(name="profile")


class ProfileStates(StatesGroup):
    entering = State()


async def _render_profile(callback: CallbackQuery, session: AsyncSession) -> None:
    overview = await profile.scores_overview(session, callback.from_user.id)
    await callback.message.edit_text(texts.profile_text(overview), reply_markup=kb.profile_kb(overview))


@router.callback_query(MenuCb.filter(F.to == "profile"))
async def open_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.set_state(None)
    await _render_profile(callback, session)
    await callback.answer()


@router.callback_query(ProfileCb.filter(F.action == "clear"))
async def clear_profile(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await profile.clear_scores(session, callback.from_user.id)
    await state.set_state(None)
    await _render_profile(callback, session)
    await callback.answer("Баллы очищены")


@router.callback_query(ScoreSubjCb.filter())
async def ask_score(
    callback: CallbackQuery, callback_data: ScoreSubjCb, session: AsyncSession, state: FSMContext
) -> None:
    subject = await session.get(m.ExamSubject, callback_data.subject_id)
    if subject is None:
        await callback.answer("Предмет не найден", show_alert=True)
        return
    await state.set_state(ProfileStates.entering)
    await state.update_data(
        subject_id=subject.id,
        prompt_chat=callback.message.chat.id,
        prompt_msg=callback.message.message_id,
    )
    await callback.message.edit_text(
        f"Введите ваш балл по предмету «{subject.name}» — число от 0 до 100.\n"
        "Отправьте его сообщением.",
        reply_markup=kb.cancel_score_kb(),
    )
    await callback.answer()


@router.message(ProfileStates.entering, F.text)
async def receive_score(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    subject_id = data.get("subject_id")
    prompt_chat = data.get("prompt_chat")
    prompt_msg = data.get("prompt_msg")
    raw = message.text.strip()

    # убираем сообщение пользователя, чтобы не засорять чат (в личке боту это разрешено)
    try:
        await message.delete()
    except TelegramBadRequest:
        pass

    subject = await session.get(m.ExamSubject, subject_id) if subject_id else None
    if subject is None:
        await state.set_state(None)
        return

    if not raw.isdigit() or not (0 <= int(raw) <= 100):
        await _safe_edit(
            message,
            prompt_chat,
            prompt_msg,
            f"Неверный балл. Введите число от 0 до 100 по предмету «{subject.name}».",
            kb.cancel_score_kb(),
        )
        return

    await profile.set_score(session, message.from_user.id, subject_id, int(raw))
    await state.set_state(None)
    overview = await profile.scores_overview(session, message.from_user.id)
    await _safe_edit(
        message, prompt_chat, prompt_msg, texts.profile_text(overview), kb.profile_kb(overview)
    )


async def _safe_edit(message: Message, chat_id, msg_id, text, markup) -> None:
    """Отредактировать сообщение-приглашение; если не вышло — отправить новое."""
    try:
        await message.bot.edit_message_text(
            chat_id=chat_id, message_id=msg_id, text=text, reply_markup=markup
        )
    except TelegramBadRequest:
        await message.answer(text, reply_markup=markup)
