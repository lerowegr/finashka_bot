from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.bot import keyboards as kb
from app.bot import texts
from app.bot.callbacks import MenuCb, NoopCb

router = Router(name="start")


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.MAIN_MENU, reply_markup=kb.main_menu_kb())


@router.callback_query(MenuCb.filter(F.to == "main"))
async def back_to_main(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.MAIN_MENU, reply_markup=kb.main_menu_kb())
    await callback.answer()


@router.callback_query(NoopCb.filter())
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
