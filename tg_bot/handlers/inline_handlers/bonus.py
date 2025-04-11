from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.service.api_requests import get_bonus_by_id, get_client_bonuses

bonuses_router = Router()


@bonuses_router.callback_query(F.data == "client_bonuses")
async def bonuses_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Бонусы".
    Отправляет список бонусов для клиентов.
    """
    bonuses = await get_client_bonuses()
    if not bonuses:
        await callback.message.answer("Список бонусов пуст.")
        await callback.answer()
        return

    # Создаем клавиатуру с бонусами
    keyboard = InlineKeyboardBuilder()
    for bonus in bonuses:
        keyboard.button(text=bonus["bonus"], callback_data=f"bonus_{bonus['id']}")
    keyboard.button(text="Назад", callback_data="inline_main_menu")
    keyboard.adjust(1)

    await callback.message.answer("Ваши бонусы:", reply_markup=keyboard.as_markup())
    await callback.answer()


@bonuses_router.callback_query(F.data.startswith("bonus_"))
async def handle_bonus_selection(callback: CallbackQuery):
    """
    Обработчик выбора бонуса.
    Отправляет информацию о бонусе.
    """
    bonus_id = callback.data.split("_")[-1]
    bonus = await get_bonus_by_id(bonus_id)  # Реализуйте функцию get_bonus_by_id
    if not bonus:
        await callback.message.answer("Информация о бонусе не найдена.")
        await callback.answer()
        return

    formatted_text = f"""
    <b>Бонус:</b> {bonus['bonus']}
    <b>Описание:</b> {bonus['description']}
    """

    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Назад", callback_data="client_bonuses")
    keyboard.adjust(1)

    await callback.message.answer(formatted_text, reply_markup=keyboard.as_markup())
    await callback.answer()
