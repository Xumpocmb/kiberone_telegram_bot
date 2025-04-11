from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.service.api_requests import find_user_in_django, get_sales_managers_by_branch

sales_manager_router = Router()


@sales_manager_router.callback_query(F.data == "sales_managers")
async def sales_managers_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Менеджеры по продажам".
    Отправляет список менеджеров для филиала пользователя.
    """
    telegram_id = callback.from_user.id

    # Получаем данные пользователя из Django
    user_data = await find_user_in_django(telegram_id)
    if not user_data or not user_data.get("success"):
        await callback.message.answer(
            "Ошибка: не удалось получить данные пользователя."
        )
        await callback.answer()
        return

    # Извлекаем информацию о пользователе
    user = user_data.get("user", {})
    clients = user.get("clients", [])

    # Проверяем, есть ли клиенты у пользователя
    if not clients:
        await callback.message.answer("У вас нет привязанных клиентов.")
        await callback.answer()
        return

    # Выбираем первого клиента с приоритетом (например, активного клиента)
    active_client = next((client for client in clients if client.get("is_study")), None)
    if not active_client:
        active_client = clients[0]  # Если нет активных клиентов, берем первого

    # Проверяем, есть ли у клиента привязанный филиал
    branch_id = active_client.get("branch_id")
    if not branch_id:
        await callback.message.answer("У вашего клиента нет привязанного филиала.")
        await callback.answer()
        return

    # Получаем менеджеров для филиала
    managers = await get_sales_managers_by_branch(branch_id)
    if not managers:
        await callback.message.answer("Список менеджеров пуст.")
        await callback.answer()
        return

    # Создаем клавиатуру с менеджерами
    keyboard = InlineKeyboardBuilder()
    for manager in managers:
        keyboard.button(text=manager["name"], url=manager["telegram_link"])
    keyboard.button(text="Назад", callback_data="inline_main_menu")
    keyboard.adjust(1)

    await callback.message.answer(
        "Наши менеджеры по продажам:", reply_markup=keyboard.as_markup()
    )
    await callback.answer()
