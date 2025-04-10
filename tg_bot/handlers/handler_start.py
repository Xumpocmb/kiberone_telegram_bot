import json
import re
import os
import aiohttp
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

from tg_bot.keyboards.inline_keyboards.inline_keyboard_main_menu import (
    main_menu_inline_keyboard_for_client,
    main_menu_inline_keyboard_for_lead_with_group,
    main_menu_inline_keyboard_for_lead_without_group,
)

from tg_bot.filters.filter_admin import IsAdmin
from tg_bot.configs.logger_config import get_logger
from tg_bot.service.api_requests import (
    create_or_update_clients_from_crm,
    find_user_in_crm,
    find_user_in_django,
    register_user_in_crm,
    register_user_in_db,
)

logger = get_logger()

start_router: Router = Router()

DJANGO_API_URL = os.getenv("KIBER_API_URL")


USER_STATUS_CLIENT = "2"
USER_STATUS_LEAD_WITH_GROUP = "1"
USER_STATUS_LEAD_WITHOUT_GROUP = "0"


keyboards_by_status = {
    USER_STATUS_CLIENT: main_menu_inline_keyboard_for_client,
    USER_STATUS_LEAD_WITH_GROUP: main_menu_inline_keyboard_for_lead_with_group,
    USER_STATUS_LEAD_WITHOUT_GROUP: main_menu_inline_keyboard_for_lead_without_group,
}

# -----------------------------------------------------------

# ХЕНДЛЕР СТАРТ

# -----------------------------------------------------------


@start_router.message(IsAdmin(), CommandStart())
async def admin_start_handler(message: Message) -> None:
    await message.answer("Привет, администратор!")


@start_router.message(CommandStart())
async def user_start_handler(message: Message):
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

    telegram_id = message.from_user.id

    await message.answer(
        "Добро пожаловать в KIBERone!☺️\n"
        "Мы рады видеть вас снова!☺️\n"
        "Сейчас мы немножечко поколдуем для Вас ✨ Ожидайте\n"
        ""
    )

    find_result: dict | None = await find_user_in_django(telegram_id)
    if find_result is None:
        await message.answer(
            f"Упс.. У нас возникла ошибка при поиске в базе данных..\nПопробуйте ещё раз."
        )
        return
    if find_result.get("success", False):
        logger.info("Пользователь найден в БД. Обновим данные")
        db_user: dict | None = find_result.get("user", None)
        if db_user:
            await handle_existing_user(message, db_user)
    else:
        logger.info("Пользователь не найден в БД. Запрашиваем контакт")
        greeting = f"Привет, {message.from_user.username}!\n{formatted_message}"
        filename = "files/contact_image.png"
        file = types.FSInputFile(filename)
        contact_keyboard = ReplyKeyboardMarkup(
            resize_keyboard=True,
            keyboard=[
                [KeyboardButton(text="Поделиться контактом", request_contact=True)]
            ],
        )
        await message.answer(greeting, reply_markup=contact_keyboard)
        await message.answer_photo(
            file, caption="Поделитесь своим контактом с KIBERone"
        )


async def handle_existing_user(message, db_user: dict):
    if not isinstance(db_user, dict) or "id" not in db_user:
        await message.answer("Ошибка: некорректные данные пользователя.")
        return

    phone_number = db_user.get("phone_number", "")
    username = db_user.get("username", "")
    telegram_id = db_user.get("telegram_id", "")

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)

    # Получаем актуальный статус пользователя
    updated_db_user: dict = await find_user_in_django(telegram_id)
    if not updated_db_user:
        await message.answer(
            "Ошибка: не удалось получить актуальные данные пользователя."
        )
        return

    user_status = updated_db_user.get("status", "0")  # По умолчанию "Lead"
    logger.info(f"Пользователь {username} имеет статус: {user_status}")

    # Отправляем клавиатуру в зависимости от статуса
    if user_status == "2":  # Клиент
        await message.answer(
            "Вы клиент!", reply_markup=main_menu_inline_keyboard_for_client
        )
    elif user_status == "1":  # Lead with group
        await message.answer(
            "Вы потенциальный клиент с группой!",
            reply_markup=main_menu_inline_keyboard_for_lead_with_group,
        )
    else:  # Lead
        await message.answer(
            "Вы потенциальный клиент!",
            reply_markup=main_menu_inline_keyboard_for_lead_without_group,
        )


@start_router.message(F.contact)
async def handle_contact(message: Message):
    """
    Обработчик контакта.
    Выполняет следующие действия:
    1. Получает информацию о пользователе из Telegram.
    2. Ищет пользователя в базе данных Django.
    3. Если пользователь не найден, регистрирует его в базе данных Django.
    4. Ищет пользователя в CRM системе.
    5. Если пользователь не найден в CRM, регистрирует его.
    6. Обновляет данные о клиентах из CRM в базе данных Django.
    7. Отправляет приветственное сообщение с клавиатурой, зависящей от статуса пользователя.
    """
    tg_user: types.User = message.from_user
    telegram_id: int = message.contact.user_id
    username: str = tg_user.username
    phone_number: str = str(re.sub(r"\D", "", message.contact.phone_number))

    # Поиск в БД Django
    find_result: dict | None = await find_user_in_django(telegram_id)
    print(find_result)
    if find_result.get("success", False) is False:
        registration_result: dict = await register_user_in_db(
            telegram_id, username, phone_number
        )
        print(registration_result)
        if registration_result.get("success", False):
            db_user: dict | None = registration_result.get("user", None)
            print(db_user)
            await message.answer(
                "Ваш контакт сохранен! 😊\nМы подготавливаем для Вас данные.\nЕще пару секундочек..",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await message.answer(
                f"Упс.. У нас возникла ошибка при регистрации..\nПопробуйте ещё раз."
            )
            return
    else:
        db_user: dict | None = find_result.get("user", None)

    if not db_user or not isinstance(db_user, dict) or "id" not in db_user:
        logger.error(f"Некорректные данные пользователя: {db_user}")
        await message.answer(
            "Ошибка: некорректные данные пользователя.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)

    # Получаем актуальный статус пользователя
    updated_db_user: dict = await find_user_in_django(telegram_id)
    if not updated_db_user:
        await message.answer(
            "Упс.. Мы не смогли получить актуальные данные пользователя.\nПопробуйте ещё раз.",
            reply_markup=ReplyKeyboardRemove(),
        )
        return

    user_status = updated_db_user.get("status", "0")  # По умолчанию "Lead"
    logger.info(f"Пользователь {username} имеет статус: {user_status}")

    # Отправляем клавиатуру в зависимости от статуса
    keyboard = keyboards_by_status.get(
        user_status, main_menu_inline_keyboard_for_lead_without_group
    )
    await message.answer("Вот ваше главное меню:", reply_markup=keyboard)


# -----------------------------------------------------------

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ОБРАБОТКИ ИНФОРМАЦИИ

# -----------------------------------------------------------


# Поиск в црм, создание и обновление в БД
async def handle_crm_lookup(message: Message, phone_number: str, db_user: dict):
    try:
        logger.info(f"Поиск пользователя в CRM по номеру телефона: {phone_number}")
        search_crm_response: dict = await find_user_in_crm(phone_number)
        # регистрация в црм
        if not search_crm_response:
            logger.warning(f"Пользователь с телефоном {phone_number} не найден в CRM.")
            await message.answer("Вы не зарегистрированы в CRM.\nРегистрируем...")
            register_response: dict = await register_user_in_crm(message, phone_number)
            crm_items: list = parse_crm_response(register_response)

            logger.info("Обновление пользователя в БД после регистрации в црм")
            response_data: dict = await create_or_update_clients_from_crm(
                db_user, crm_items
            )
            if not response_data:
                await message.answer(
                    "Не удалось обновить данные клиентов. Попробуйте позже."
                )
                return
            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            await message.answer(
                f"Создано новых клиентов: {created}\n"
                f"Обновлено клиентов: {updated}\n"
                f"Удалено клиентов: {deleted}"
            )
            await message.answer(
                "Актуальность данных проверена!", reply_markup=ReplyKeyboardRemove()
            )
            return

        # обновление в црм
        await message.answer("Мы проверим актуальность данных.. Колдую 🪄!")
        total_clients: int = search_crm_response.get("total", 0)
        items: list = search_crm_response.get("items", [])

        if total_clients == 0:
            return
        else:
            response_data = await create_or_update_clients_from_crm(db_user, items)
            if not response_data:
                await message.answer(
                    "Упс, сломалось.. 🥺 Не удалось обновить данные. Попробуйте позже."
                )
                return

            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            logger.info(
                f"Результат обновления данных: created:{created}, updated:{updated}, deleted:{deleted}"
            )
            await message.answer("Актуальность данных проверена! 💫")

    except Exception as e:
        logger.error(f"Ошибка при работе с CRM: {str(e)}")
        await message.answer(
            "Упс, сломалось.. 🥺 Не удалось проверить ваши данные. Попробуйте позже."
        )


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
