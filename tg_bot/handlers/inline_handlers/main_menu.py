from tg_bot.configs.logger_config import get_logger


from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
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

    # Поиск пользователя в базе данных Django
    find_result = await find_user_in_django(telegram_id)
    if not find_result or not find_result.get("success"):
        logger.error(f"Ошибка при поиске пользователя в БД: {find_result}")
        await message.answer(
            "Вы не зарегистрированы в системе. Пожалуйста, начните с команды /start."
        )
        return

    db_user = find_result.get("user")
    if not db_user or "id" not in db_user:
        logger.error(f"Некорректные данные пользователя: {db_user}")
        await message.answer("Ошибка: некорректные данные пользователя.")
        return

    # Получение актуального статуса пользователя
    user_status = db_user.get("status", "0")  # По умолчанию "Lead"
    logger.info(f"Пользователь {db_user.get('username')} имеет статус: {user_status}")

    # Отправка клавиатуры в зависимости от статуса
    keyboard = keyboards_by_status.get(
        user_status, main_menu_inline_keyboard_for_lead_without_group
    )
    await message.answer("Вот ваше главное меню:", reply_markup=keyboard)
