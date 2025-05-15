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
formatted_message = """
            Вас приветствует Международная КиберШкола программирования для детей от 6 до 14 лет  KIBERone! 
            Мы точно знаем, чему учить детей, чтобы это было актуально через 20 лет!
            ✅ Цифровая грамотность: Основы программирования, управление данными, работа с нейросетями и искусственным интеллектом;
            ✅ Финансовая грамотность: управление личными финансами;
            ✅ Критическое мышление и решение проблем: умение анализировать информацию и находить решения сложных задач;
            ✅ Эмоциональный интеллект: навыки общения, управление эмоциями и работа в команде.

            <b>Предупреждение о сборе информации и обработке персональных данных</b>\n

            Дорогой пользователь! При использовании нашего бота, учтите следующее:
            1. <b>Сбор информации</b>: Мы можем собирать определенные данные о вас, такие как ваш ID пользователя, имя, фамилию, номер телефона (если вы поделились контактом) и другие данные, необходимые для функционирования бота.
            2. <b>Обработка персональных данных</b>: Ваши персональные данные будут использоваться только в рамках функциональности бота. Мы не передаем их третьим лицам и не используем для рекламных целей.
            3. <b>Информационная безопасность</b>: Мы прилагаем все усилия для обеспечения безопасности ваших данных. Однако, помните, что интернет не всегда безопасен, и мы не можем гарантировать абсолютную защиту.
            4. <b>Согласие</b>: Используя нашего бота, вы соглашаетесь с нашей политикой конфиденциальности и обработкой данных.
            \n\n\n
            <b>Нажмите кнопку "Поделиться контактом", чтобы отправить свой контакт.</b>

            <b>С уважением, KIBERone!</b>
            """

@start_router.message(IsAdmin(), CommandStart())
async def admin_start_handler(message: Message) -> None:
    await message.answer("Привет, администратор!\n"
                         "Ссылка на админ панель: #")


@start_router.message(CommandStart())
async def user_start_handler(message: Message):
    telegram_id: str = str(message.from_user.id)

    await message.answer(
        "Добро пожаловать в KIBERone!☺️\n"
        "Я очень рад видеть Вас снова!☺️\n"
        "Сейчас я немножечко поколдую для Вас ✨ Ожидайте\n"
        ""
    )

    find_result: dict | None = await find_user_in_django(telegram_id)
    if find_result is not None:
        if find_result.get("success"):
            logger.info("Пользователь найден в БД. Обновим данные")
            db_user: dict | None = find_result.get("user", None)
            if db_user:
                await handle_existing_user(message, db_user)
        else:
            logger.info("Пользователь не найден в БД. Запрашиваем контакт")
            greeting = f"Привет, {message.from_user.username}!\n{formatted_message}"
            filename = os.path.abspath("tgbot/files/contact_image.png")
            if not os.path.exists(filename):
                print(f"❌ Файл не найден: {filename}")
            else:
                print(f"✅ Файл найден: {filename}")
            file = types.FSInputFile(filename)
            contact_keyboard = ReplyKeyboardMarkup(
                resize_keyboard=True,
                keyboard=[
                    [KeyboardButton(text="⚡️Поделиться контактом⚡️", request_contact=True)]
                ],
            )
            await message.answer(greeting, reply_markup=contact_keyboard)
            await message.answer_photo(
                file, caption="Поделитесь своим контактом с KIBERone"
            )
    else:
        await message.answer(f"Упс.. У нас возникла ошибка с сервисом хранения Кибер-данных..\nПопробуйте ещё раз.")


async def handle_existing_user(message, db_user: dict):
    if not isinstance(db_user, dict) or "id" not in db_user:
        await message.answer("Ошибка: некорректные данные пользователя.")
        return

    phone_number = db_user.get("phone_number", "")
    telegram_id: str = db_user.get("telegram_id", "")

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)
    await message.answer("Вот мое меню 🤗:", reply_markup=await get_user_keyboard(telegram_id))


@start_router.message(F.contact)
async def handle_contact(message: Message):
    """
    Обработчик контакта.
    """
    tg_user: types.User = message.from_user
    telegram_id: str = str(message.contact.user_id)
    username: str = tg_user.username
    phone_number: str = str(re.sub(r"\D", "", message.contact.phone_number))

    # Поиск в БД Django
    find_result: dict | None = await find_user_in_django(telegram_id)
    if find_result.get("success", False) is False:
        registration_result: dict = await register_user_in_db(telegram_id, username, phone_number)
        if registration_result.get("success", False):
            db_user: dict | None = registration_result.get("user", None)
            await message.answer("Ваш контакт сохранен! 😊\nЯ подготавливаем для Вас данные.\nЕще пару секундочек..",
                                 reply_markup=ReplyKeyboardRemove())
        else:
            await message.answer(f"Упс.. У нас возникла ошибка при регистрации..\nПопробуйте ещё раз.")
            return
    else:
        db_user: dict | None = find_result.get("user", None)

    if not db_user or not isinstance(db_user, dict) or "id" not in db_user:
        logger.error(f"Некорректные данные пользователя: {db_user}")
        await message.answer("Ошибка: некорректные данные пользователя.", reply_markup=ReplyKeyboardRemove())
        return

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)

    # Получаем актуальный статус пользователя
    updated_db_user: dict = await find_user_in_django(telegram_id)
    if not updated_db_user:
        await message.answer(
            "Упс.. Я не смог получить актуальные данные пользователя😔.\nПопробуйте ещё раз.",
            reply_markup=ReplyKeyboardRemove(), )
        return

    user_status = updated_db_user.get("status", "0")  # По умолчанию "Lead"
    logger.info(f"Пользователь {username} имеет статус: {user_status}")

    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://t.me/kiberone_bel"
        )
    ]

    links = await get_user_tg_links_from_api(updated_db_user.get("telegram_id"))

    if links:
        for link in links:
            if link.startswith("https://t.me/"):
                buttons.append(InlineKeyboardButton(text="Чат группы", url=str(link)))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in buttons],
        resize_keyboard=True,
        input_field_placeholder="Перейдите по ссылкам для вступления в группы..",
    )
    await message.answer("Вот необходимые телеграм-ссылки:\n"
                                  "Перейдите в них, вступите 😊", reply_markup=keyboard)

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
            await message.answer("Вы не зарегистрированы в CRM.\nРегистрируем...")
            register_response: dict = await register_user_in_crm(message, phone_number)
            crm_items: list = parse_crm_response(register_response)

            logger.info("Обновление пользователя в БД после регистрации в црм")
            response_data: dict = await create_or_update_clients_from_crm(db_user, crm_items)
            if not response_data:
                await message.answer("Не удалось обновить данные клиентов. Попробуйте позже.")
                return
            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            await message.answer(
                f"Создано новых клиентов: {created}\n"f"Обновлено клиентов: {updated}\n"f"Удалено клиентов: {deleted}")
            await message.answer("Актуальность данных проверена!", reply_markup=ReplyKeyboardRemove())
            return

        # обновление в црм
        await message.answer("Я сейчас проверю актуальность данных..⚡️ Колдую 🪄!")
        total_clients: int = search_crm_response.get("total", 0)
        items: list = search_crm_response.get("items", [])

        if total_clients == 0:
            return
        else:
            response_data = await create_or_update_clients_from_crm(db_user, items)
            if not response_data:
                await message.answer("Упс, сломалось.. 🥺 Не удалось обновить данные. Попробуйте позже.")
                return

            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            logger.info(f"Результат обновления данных: created:{created}, updated:{updated}, deleted:{deleted}")
            await message.answer("Актуальность данных проверена! 💫")

    except Exception as e:
        logger.error(f"Ошибка при работе с CRM: {str(e)}")
        await message.answer("Упс, сломалось.. 🥺 Не удалось проверить ваши данные. Попробуйте позже.")


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
