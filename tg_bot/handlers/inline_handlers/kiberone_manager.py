from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.service.api_requests import find_user_in_django, get_sales_managers_by_branch, get_manager_by_room_id, \
    get_user_group_lessons

contact_manager_router = Router()


@contact_manager_router.callback_query(F.data == "contact_manager")
async def sales_managers_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Менеджер".
    Отправляет список менеджеров для филиала или локации пользователя.
    """
    telegram_id: str = str(callback.from_user.id)

    user_data = await find_user_in_django(telegram_id)
    if not user_data or not user_data.get("success"):
        await callback.message.answer("Упс.. не удалось получить данные. 😢")
        await callback.answer()
        return

    # Извлекаем информацию о пользователе
    user = user_data.get("user", {})
    clients = user.get("clients", [])

    if not clients:
        await callback.message.answer("Хм, у вас нет привязанных клиентов. Попробуйте начать с команды /start")
        await callback.answer()
        return

    for client in clients:
        if client.get("is_study"):
            user_crm_id = client.get("crm_id")
            branch_id = client.get("branch_id")

            if not user_crm_id or not branch_id:
                await callback.message.answer("Упс, мне недостаточно данных для получения уроков.😢")
                await callback.answer()
                return

            lessons_data = await get_user_group_lessons(user_crm_id, branch_id)
            if not lessons_data or lessons_data.get("total", 0) == 0:
                await callback.message.answer("У вас нет запланированных уроков.")
                await callback.answer()
                return

            group_lesson = lessons_data.get("items", [])[0]
            room_id = group_lesson.get("room_id")

            if not room_id:
                await callback.message.answer("Упс.. не удалось определить локацию.😢")
                await callback.answer()
                return

            manager_info = await get_manager_by_room_id(room_id)
            if not manager_info:
                await callback.message.answer("Менеджер для вашей локации не найден.😔")
                await callback.answer()
                return

            manager_name = manager_info.get("name", "Менеджер")
            manager_telegram_link = manager_info.get("telegram_link", "#")
            await callback.message.answer(
                text=f"Ваш менеджер: {manager_name}\n{manager_telegram_link}")
        else:
            branch_id = client.get("branch_id")
            if not branch_id:
                await callback.message.answer("Оказалось, что вас нет привязанного филиала.😔 Начните с команды /start")
                await callback.answer()
                return

            managers = await get_sales_managers_by_branch(branch_id)
            if not managers:
                await callback.message.answer("Список менеджеров пуст.😔")
                await callback.answer()
                return

            keyboard = InlineKeyboardBuilder()
            for manager in managers:
                keyboard.button(text=manager["name"], url=manager["telegram_link"])
            keyboard.button(text="<< Назад", callback_data="inline_main_menu")
            keyboard.adjust(1)

            await callback.message.answer(
                "Наши менеджеры:", reply_markup=keyboard.as_markup())
        await callback.answer()