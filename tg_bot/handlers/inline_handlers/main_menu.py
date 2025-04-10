from tg_bot.configs.logger_config import get_logger


from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import (
    main_menu_inline_keyboard_for_client,
    main_menu_inline_keyboard_for_lead_with_group,
    main_menu_inline_keyboard_for_lead_without_group,
)
from tg_bot.service.api_requests import find_user_in_django


logger = get_logger()
main_menu_router: Router = Router()

USER_STATUS_CLIENT = "2"
USER_STATUS_LEAD_WITH_GROUP = "1"
USER_STATUS_LEAD_WITHOUT_GROUP = "0"


keyboards_by_status = {
    USER_STATUS_CLIENT: main_menu_inline_keyboard_for_client,
    USER_STATUS_LEAD_WITH_GROUP: main_menu_inline_keyboard_for_lead_with_group,
    USER_STATUS_LEAD_WITHOUT_GROUP: main_menu_inline_keyboard_for_lead_without_group,
}


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

    await message.answer("Вот ваше главное меню:", reply_markup=keyboard)


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
        return keyboards_by_status.get(
            user_status, main_menu_inline_keyboard_for_lead_without_group
        )

    except Exception as e:
        logger.error(f"Ошибка при получении клавиатуры пользователя: {e}")
        return None
