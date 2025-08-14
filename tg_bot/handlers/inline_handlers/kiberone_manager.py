from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from tg_bot.service.api_requests import find_user_in_django, get_sales_managers, get_manager, \
    get_user_group_lessons

contact_manager_router = Router()


@contact_manager_router.callback_query(F.data == "contact_manager")
async def get_managers_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Менеджер".
    """
    telegram_id = str(callback.from_user.id)

    try:
        # Получаем данные пользователя
        user_data = await find_user_in_django(telegram_id)
        if not user_data or not user_data.get("success"):
            await callback.message.answer("❌ Не удалось получить ваши данные. Попробуйте позже.")
            await callback.answer()
            return

        user = user_data.get("user", {})
        clients = user.get("clients", [])

        if not clients:
            await callback.message.answer("🔍 У нас нет ваших записей в системе. Начните с команды /start")
            await callback.answer()
            return

        # Берем первого клиента для получения информации о менеджере
        client = clients[0]
        user_crm_id = client.get("crm_id")
        branch_id = client.get("branch_id")

        if not user_crm_id or not branch_id:
            await callback.message.answer("⚠️ Недостаточно данных для поиска менеджера.")
            await callback.answer()
            return

        # Получаем информацию о менеджере
        manager_info = await get_manager(user_crm_id, branch_id)
        
        # Создаем клавиатуру для возврата в главное меню
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="« Назад в меню", callback_data="main_menu")
        
        # Проверяем наличие ответа от API
        if not manager_info:
            await callback.message.answer("⚠️ Не удалось получить информацию о менеджере. Попробуйте позже.", reply_markup=keyboard.as_markup())
            await callback.answer()
            return
            
        # Проверяем успешность запроса
        if not manager_info.get("success"):
            message = manager_info.get("message", "Не удалось получить информацию о менеджере.")
            await callback.message.answer(f"⚠️ {message}", reply_markup=keyboard.as_markup())
            await callback.answer()
            return
            
        # Проверяем наличие назначенного менеджера
        has_assigned = manager_info.get("has_assigned", False)
        if not has_assigned:
            await callback.message.answer("ℹ️ У вас нет назначенного менеджера.", reply_markup=keyboard.as_markup())
            await callback.answer()
            return
            
        # Формируем сообщение с информацией о менеджере
        manager_data = manager_info.get("data", {})
        is_study = manager_info.get("is_study", False)
        manager_name = manager_data.get("name", "Не указано")
        manager_phone = manager_data.get("phone", "Не указано")
        manager_email = manager_data.get("email", "Не указано")
        
        message_text = f"👨‍💼 <b>Ваш менеджер:</b> {manager_name}\n"
        message_text += f"📱 <b>Телефон:</b> {manager_phone}\n"
        message_text += f"📧 <b>Email:</b> {manager_email}\n"
        
        if is_study:
            message_text += "\n🎓 <i>Вы находитесь в процессе обучения.</i>"
        
        await callback.message.answer(message_text, reply_markup=keyboard.as_markup())
        await callback.answer()

    except Exception as e:
        await callback.message.answer("⚠️ Произошла ошибка. Попробуйте позже.")
        await callback.answer()
