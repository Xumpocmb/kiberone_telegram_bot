from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.service.api_requests import (
    find_user_in_django,
    get_partner_by_id,
    get_partner_categories,
    get_partners_by_category,
)


partners_router = Router()


@partners_router.callback_query(F.data == "partners_list")
async def partners_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Партнеры".
    Отправляет список категорий партнеров.
    """
    categories = await get_partner_categories()
    if not categories:
        await callback.message.answer("Список категорий пуст.")
        await callback.answer()
        return

    # Создаем клавиатуру с категориями
    keyboard = InlineKeyboardBuilder()
    for category in categories:
        keyboard.button(
            text=category["name"], callback_data=f"partner_category_{category['id']}"
        )
    keyboard.button(text="<< Назад", callback_data="inline_main_menu")
    keyboard.adjust(1)

    await callback.message.edit_text(
        "Выберите категорию:", reply_markup=keyboard.as_markup()
    )
    await callback.answer()


@partners_router.callback_query(F.data.startswith("partner_category_"))
async def handle_category_selection(callback: CallbackQuery):
    """
    Обработчик выбора категории.
    Отправляет список партнеров и их бонусов.
    """

    category_id = callback.data.split("_")[-1]
    partners = await get_partners_by_category(category_id)
    if not partners:
        await callback.message.answer("Список партнеров пуст.")
        await callback.answer()
        return

    # Создаем клавиатуру с партнерами
    keyboard = InlineKeyboardBuilder()
    for partner in partners:
        keyboard.button(
            text=partner["partner_name"], callback_data=f"partner_info_{partner['id']}"
        )
    keyboard.button(text="Назад", callback_data="partners_list")
    keyboard.adjust(1)

    await callback.message.edit_text(
        "Выберите партнера:", reply_markup=keyboard.as_markup()
    )
    await callback.answer()


@partners_router.callback_query(F.data.startswith("partner_info_"))
async def handle_partner_selection(callback: CallbackQuery):
    """
    Обработчик выбора партнера.
    Отправляет информацию о бонусах.
    """
    partner_id = callback.data.split("_")[-1]
    partner = await get_partner_by_id(partner_id)
    if not partner:
        await callback.message.answer("Информация о партнере не найдена.")
        await callback.answer()
        return

    # Проверяем статус пользователя
    user_status = await get_user_status(str(callback.from_user.id))

    if user_status == "2":
        if user_status != "2":  # Только клиенты получают промокод
            formatted_text = f"""
            <b>Партнер:</b> {partner['partner_name']}
            <b>Описание:</b> {partner['description']}
            """
        else:
            formatted_text = f"""
            <b>Партнер:</b> {partner['partner_name']}
            <b>Описание:</b> {partner['description']}
            <b>Промо-код:</b> {partner['code']}
            """
    else:
        formatted_text = "Информация доступна только резидентам!"

    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="<< Назад", callback_data=f"partner_category_{partner['category']}"
    )
    keyboard.adjust(1)

    await callback.message.edit_text(formatted_text, reply_markup=keyboard.as_markup())
    await callback.answer()


async def get_user_status(telegram_id: str) -> str:
    """
    Получает статус пользователя из базы данных Django.
    """
    user_data = await find_user_in_django(telegram_id)
    if user_data and user_data.get("success"):
        user = user_data.get("user", {})
        return user.get("status", "0")
    return "0"
