from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup

from tg_bot.configs.logger_config import get_logger
from tg_bot.keyboards.inline_keyboards.inline_keyboard_menu_bonuses import \
    get_clients_bonuses_menu_inline_for_lead_keyboard, get_clients_bonuses_menu_inline_keyboard
from tg_bot.service.api_requests import find_user_in_django

logger = get_logger()

menu_bonuses_router = Router()


@menu_bonuses_router.callback_query(F.data == "menu_bonuses")
async def send_menu_bonuses(callback_query: CallbackQuery):
    telegram_id = callback_query.from_user.id
    find_result = await find_user_in_django(telegram_id)
    if not find_result or not find_result.get("success"):
        logger.error(f"Ошибка при поиске пользователя в БД: {find_result}")
        return None

    db_user = find_result.get("user")
    if not db_user or "id" not in db_user:
        logger.error(f"Некорректные данные пользователя: {db_user}")
        return None

    user_status = db_user.get("status", "0")
    logger.info(f"Пользователь с ID {telegram_id} имеет статус: {user_status}")

    if user_status == "2":
        await callback_query.message.edit_text("Бонусы для наших резидентов:", reply_markup=get_clients_bonuses_menu_inline_keyboard())
    else:
        await callback_query.message.edit_text("Бонусы для наших резидентов:", reply_markup=get_clients_bonuses_menu_inline_for_lead_keyboard())
    await callback_query.answer()
