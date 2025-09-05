import json
import os
import re

from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup,
)

from tg_bot.configs.logger_config import get_logger
from tg_bot.configs.bot_messages import *
from tg_bot.filters.filter_admin import IsAdmin
from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from tg_bot.service.api_requests import (
    create_or_update_clients_from_crm,
    find_user_in_crm,
    find_user_in_django,
    register_user_in_crm,
    register_user_in_db, get_user_tg_links_from_api,
)

logger = get_logger()

start_router: Router = Router()




# -----------------------------------------------------------

# ХЕНДЛЕР СТАРТ

# -----------------------------------------------------------
# Используем сообщение из файла bot_messages.py

@start_router.message(IsAdmin(), CommandStart())
async def admin_start_handler(message: Message) -> None:
    await message.answer(START_ADMIN_GREETING)


@start_router.message(CommandStart())
async def user_start_handler(message: Message):
    telegram_id: str = str(message.from_user.id)

    await message.answer(START_WELCOME)

    find_result: dict | None = await find_user_in_django(telegram_id)
    if find_result is not None:
        if find_result.get("success"):
            logger.info("Пользователь найден в БД. Обновим данные")
            db_user: dict | None = find_result.get("user", None)
            if db_user:
                await handle_existing_user(message, db_user)
        else:
            logger.info("Пользователь не найден в БД. Запрашиваем контакт")
            greeting = f"Привет, {message.from_user.username}!\n{FORMATTED_WELCOME_MESSAGE}"
            filename = os.path.abspath("tg_bot/files/contact_image.png")
            file = types.FSInputFile(filename)
            contact_keyboard = ReplyKeyboardMarkup(
                resize_keyboard=True,
                keyboard=[
                    [KeyboardButton(text=START_CONTACT_BUTTON, request_contact=True)]
                ],
            )
            await message.answer(greeting, reply_markup=contact_keyboard)
            await message.answer_photo(
                file, caption=START_CONTACT_CAPTION
            )
    else:
        await message.answer(START_ERROR_SERVICE)


async def handle_existing_user(message, db_user: dict):
    if not isinstance(db_user, dict) or "id" not in db_user:
        await message.answer(START_ERROR_USER_DATA)
        return

    phone_number = db_user.get("phone_number", "")
    telegram_id: str = db_user.get("telegram_id", "")

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)

    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://t.me/kiberone_bel"
        )
    ]

    links = await get_user_tg_links_from_api(telegram_id)

    if links:
        for link in links:
            if link.startswith("https://t.me/"):
                buttons.append(InlineKeyboardButton(text="Чат группы", url=str(link)))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in buttons],
        resize_keyboard=True,
        input_field_placeholder="Перейдите по ссылкам для вступления в группы..",
    )
    await message.answer(START_TELEGRAM_LINKS, reply_markup=keyboard)

    await message.answer(START_MENU, reply_markup=await get_user_keyboard(telegram_id))


@start_router.message(F.contact)
async def handle_contact(message: Message):
    """
    Обработчик контакта.
    """
    tg_user: types.User = message.from_user
    telegram_id: str = str(message.contact.user_id)
    username: str = tg_user.username if tg_user.username else "nousername"
    phone_number: str = str(re.sub(r"\D", "", message.contact.phone_number))

    # Поиск в БД Django
    find_result: dict | None = await find_user_in_django(telegram_id)
    if find_result.get("success", False) is False:
        registration_result: dict = await register_user_in_db(telegram_id, username, phone_number)
        if registration_result.get("success", False):
            db_user: dict | None = registration_result.get("user", None)
            await message.answer(START_CONTACT_SAVED,
                                 reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(START_ERROR_REGISTRATION)
            return
    else:
        db_user: dict | None = find_result.get("user", None)

    if not db_user or not isinstance(db_user, dict) or "id" not in db_user:
        logger.error(f"Некорректные данные пользователя: {db_user}")
        await message.answer(START_ERROR_USER_DATA, reply_markup=ReplyKeyboardRemove())
        return

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)

    # Получаем актуальный статус пользователя
    updated_db_user: dict = await find_user_in_django(telegram_id)
    if not updated_db_user:
        await message.answer(
            START_ERROR_UPDATE_DATA,
            reply_markup=ReplyKeyboardRemove(), )
        return

    user_status = updated_db_user.get("status", "0")  # По умолчанию "Lead"
    logger.info(f"Пользователь {username} имеет статус: {user_status}")

    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://t.me/kiberone_bel"
        )
    ]

    links = await get_user_tg_links_from_api(telegram_id)

    if links:
        for link in links:
            if link.startswith("https://t.me/"):
                buttons.append(InlineKeyboardButton(text="Чат группы", url=str(link)))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in buttons],
        resize_keyboard=True,
        input_field_placeholder=TG_LINKS_PLACEHOLDER,
    )
    await message.answer(START_TELEGRAM_LINKS, reply_markup=keyboard)

    # # Отправляем клавиатуру в зависимости от статуса
    # await message.answer("Вот мое меню 🤗:", reply_markup=await get_user_keyboard(telegram_id))


# -----------------------------------------------------------

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ОБРАБОТКИ ИНФОРМАЦИИ

# -----------------------------------------------------------


# Поиск в црм, создание и обновление в БД
async def handle_crm_lookup(message: Message, phone_number: str, db_user: dict):
    try:
        logger.info(f"Поиск пользователя в CRM по номеру телефона: {phone_number}")
        search_crm_response: dict = await find_user_in_crm(phone_number)
        if not search_crm_response:
            logger.warning(f"Пользователь с телефоном {phone_number} не найден в CRM.")
            await message.answer(CRM_NOT_REGISTERED)
            register_response: dict = await register_user_in_crm(message, phone_number)
            crm_items: list = parse_crm_response(register_response)

            logger.info("Обновление пользователя в БД после регистрации в црм")
            response_data: dict = await create_or_update_clients_from_crm(db_user, crm_items)
            if not response_data:
                await message.answer(CRM_UPDATE_FAILED)
                return
            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            await message.answer(CRM_INFO_UPDATED, reply_markup=ReplyKeyboardRemove())
            return

        # обновление в црм
        await message.answer(CRM_CHECKING_DATA)
        total_clients: int = search_crm_response.get("total", 0)
        items: list = search_crm_response.get("items", [])

        if total_clients == 0:
            return
        else:
            response_data = await create_or_update_clients_from_crm(db_user, items)
            if not response_data:
                await message.answer(CRM_UPDATE_ERROR)
                return

            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            logger.info(f"Результат обновления данных: created:{created}, updated:{updated}, deleted:{deleted}")
            await message.answer(CRM_INFO_UPDATED_STAR)

    except Exception as e:
        logger.error(f"Ошибка при работе с CRM: {str(e)}")
        await message.answer(CRM_CHECK_ERROR)


def parse_crm_response(register_response: dict) -> list:
    """
    Преобразует ответ от CRM в список словарей.
    """
    data: list = register_response.get("data", [])
    crm_items: list = []

    # Объединяем все строки в одну
    full_json_str = "".join(data)

    try:
        # Разбиваем объединенную строку на отдельные JSON-объекты
        items = json.loads(f"[{full_json_str}]")
        for item in items:
            model_data = item.get("model")
            if model_data:
                crm_items.append(model_data)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при декодировании JSON: {e}")

    return crm_items
