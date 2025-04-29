from tg_bot.configs.logger_config import get_logger


from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import (
    get_client_keyboard,
    get_lead_with_group_keyboard,
    get_lead_without_group_keyboard,
)
from tg_bot.service.api_requests import find_user_in_django


logger = get_logger()
main_menu_router: Router = Router()


@main_menu_router.message(Command("menu"))
async def menu_handler(message: Message):
    """
    Обработчик команды /menu.
    Отправляет пользователю меню в зависимости от его статуса.
    """
    telegram_id = message.from_user.id

    # Получаем клавиатуру пользователя
    keyboard = await get_user_keyboard(telegram_id)

    if not keyboard:
        await message.answer(
            "Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start."
        )
        return

    await message.answer("Вот мое меню 🤗:", reply_markup=keyboard)


@main_menu_router.callback_query(F.data == "inline_main_menu")
async def main_menu_handler(callback: CallbackQuery):
    telegram_id = callback.from_user.id

    # Получаем клавиатуру пользователя
    keyboard = await get_user_keyboard(telegram_id)
    if not keyboard:
        await callback.message.answer(
            "Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start."
        )
        return
    await callback.message.edit_text("Вот ваше главное меню:", reply_markup=keyboard)
    await callback.answer()


async def get_user_keyboard(telegram_id):
    """
    Возвращает клавиатуру в зависимости от статуса пользователя.
    """
    try:
        # Поиск пользователя в базе данных Django
        find_result = await find_user_in_django(telegram_id)
        if not find_result or not find_result.get("success"):
            logger.error(f"Ошибка при поиске пользователя в БД: {find_result}")
            return None

        db_user = find_result.get("user")
        if not db_user or "id" not in db_user:
            logger.error(f"Некорректные данные пользователя: {db_user}")
            return None

        # Получение актуального статуса пользователя
        user_status = db_user.get("status", "0")  # По умолчанию "Lead"
        logger.info(f"Пользователь с ID {telegram_id} имеет статус: {user_status}")

        # Возвращаем клавиатуру в зависимости от статуса
        if user_status == "2":  # Клиент
            return get_client_keyboard(telegram_id)
        elif user_status == "1":  # Lead с группой
            return get_lead_with_group_keyboard()
        else:  # Lead
            return get_lead_without_group_keyboard()

    except Exception as e:
        logger.error(f"Ошибка при получении клавиатуры пользователя: {e}")
        return None
