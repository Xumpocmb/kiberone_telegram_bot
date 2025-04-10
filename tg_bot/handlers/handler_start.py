import json
import re
import os
import aiohttp
from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from tg_bot.filters.filter_admin import IsAdmin
from tg_bot.configs.logger_config import get_logger

logger = get_logger()

start_router: Router = Router()

DJANGO_API_URL = os.getenv("KIBER_API_URL")

# -----------------------------------------------------------

# ХЕНДЛЕРЫ СТАРТ

# -----------------------------------------------------------

@start_router.message(IsAdmin(), CommandStart())
async def admin_start_handler(message: Message) -> None:
    await message.answer("Привет, администратор!")
    await message.answer(DJANGO_API_URL)


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

    await message.answer("Добро пожаловать в KIBERone!☺️\n"
                         "Мы рады видеть вас снова!☺️\n"
                         "Сейчас мы немножечко поколдуем для Вас ✨ Ожидайте\n"
                         "")

    find_result: dict | None = await find_user_in_django(telegram_id)
    if find_result is None:
        await message.answer(f"Упс.. У нас возникла ошибка при поиске в базе данных..\nПопробуйте ещё раз.")
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
            keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]]
        )
        await message.answer(greeting, reply_markup=contact_keyboard)
        await message.answer_photo(file, caption="Поделитесь своим контактом с KIBERone")


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
        await message.answer("Вы клиент!", reply_markup=get_client_keyboard())
    elif user_status == "1":  # Lead with group
        await message.answer(
            "Вы потенциальный клиент с группой!",
            reply_markup=get_lead_with_group_keyboard(),
        )
    else:  # Lead
        await message.answer(
            "Вы потенциальный клиент!", reply_markup=get_lead_keyboard()
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
    phone_number: str = str(re.sub(r'\D', '', message.contact.phone_number))

    # Поиск в БД Django
    find_result: dict | None = await find_user_in_django(telegram_id)
    print(find_result)
    if find_result.get("success", False) is False:
        registration_result: dict = await register_user_in_db(telegram_id, username, phone_number)
        print(registration_result)
        if registration_result.get("success", False):
            db_user: dict | None = registration_result.get("user", None)
            print(db_user)
            await message.answer("Ваш контакт сохранен! 😊\nМы подготавливаем для Вас данные.\nЕще пару секундочек..")
        else:
            await message.answer(f"Упс.. У нас возникла ошибка при регистрации..\nПопробуйте ещё раз.")
            return
    else:
        db_user: dict | None = find_result.get("user", None)

    if not db_user or not isinstance(db_user, dict) or "id" not in db_user:
        logger.error(f"Некорректные данные пользователя: {db_user}")
        await message.answer("Ошибка: некорректные данные пользователя.")
        return

    # Поиск в црм, создание и обновление в БД
    await handle_crm_lookup(message, phone_number, db_user)

    # Получаем актуальный статус пользователя
    updated_db_user: dict = await find_user_in_django(telegram_id)
    if not updated_db_user:
        await message.answer(
            "Упс.. Мы не смогли получить актуальные данные пользователя.\nПопробуйте ещё раз."
        )
        return

    user_status = updated_db_user.get("status", "0")  # По умолчанию "Lead"
    logger.info(f"Пользователь {username} имеет статус: {user_status}")

    # Отправляем клавиатуру в зависимости от статуса
    if user_status == "2":  # Клиент
        await message.answer("Все готово к работе!\nВот мое главное меню:", reply_markup=get_client_keyboard())
    elif user_status == "1":  # Lead with group
        await message.answer(
            "Все готово к работе!⚡️\nВот мое главное меню:",
            reply_markup=get_lead_with_group_keyboard(),
        )
    else:  # Lead
        await message.answer(
            "Все готово к работе!⚡️\nВот мое главное меню:", reply_markup=get_lead_keyboard()
        )

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
            response_data: dict = await create_or_update_clients_from_crm(db_user, crm_items)
            if not response_data:
                await message.answer("Не удалось обновить данные клиентов. Попробуйте позже.")
                return
            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            await message.answer(
                f"Создано новых клиентов: {created}\n"
                f"Обновлено клиентов: {updated}\n"
                f"Удалено клиентов: {deleted}"
            )
            await message.answer("Актуальность данных проверена!")
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
                await message.answer("Упс, сломалось.. 🥺 Не удалось обновить данные. Попробуйте позже.")
                return

            created = response_data.get("created", 0)
            updated = response_data.get("updated", 0)
            deleted = response_data.get("deleted", 0)
            logger.info(f"Результат обновления данных: created:{created}, updated:{updated}, deleted:{deleted}")
            await message.answer("Актуальность данных проверена! 💫")

    except Exception as e:
        logger.error(f"Ошибка при работе с CRM: {str(e)}")
        await message.answer("Упс, сломалось.. 🥺 Не проверить ваши данные. Попробуйте позже.")


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


# -----------------------------------------------------------

# ОТПРАВКА ЗАПРОСОВ НА АПИ

# -----------------------------------------------------------


async def find_user_in_django(telegram_id) -> dict | None:
    try:
        async with aiohttp.ClientSession() as session:
            data = {"telegram_id": telegram_id}
            async with session.post(
                f"{DJANGO_API_URL}api/find_user_in_db/", json=data
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("success") and "user" in response_data:
                        logger.info(
                            f"Пользователь найден в БД"
                        )
                        return response_data
                    else:
                        logger.info(
                            f"Пользователь с telegram_id {telegram_id} не найден в БД."
                        )
                        return response_data
                else:
                    logger.error(
                        f"Ошибка при поиске пользователя в БД: {await response.json()}"
                    )
                    return None
    except Exception as e:
        logger.error(f"Не удалось выполнить запрос к БД: {e}")
        return None


async def register_user_in_db(telegram_id: int, username: str, phone_number: str) -> dict | None:
    url = f"{DJANGO_API_URL}api/register_user_in_db/"
    data = {
        "telegram_id": str(telegram_id),
        "username": username,
        "phone_number": phone_number,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status in [200, 201]:
                    response_data = await response.json()
                    if response_data.get("success") and "user" in response_data:
                        logger.info(
                            "Пользователь успешно зарегистрирован в базе данных Django."
                        )
                        return response_data
                    else:
                        logger.error(
                            f"Ошибка регистрации пользователя: {response_data.get('message')}"
                        )
                        return None
                else:
                    error_message = (await response.json()).get(
                        "message", "Неизвестная ошибка"
                    )
                    logger.error(f"Ошибка регистрации пользователя: {error_message}")
                    return None
    except Exception as e:
        logger.error(f"Не удалось выполнить запрос к Django: {e}")
        return {"success": False, "error": str(e)}


async def find_user_in_crm(phone_number) -> dict | None:
    """
    Поиск пользователя в CRM. Функция посредник, для вызова API.
    """
    async with aiohttp.ClientSession() as session:
        url = f"{DJANGO_API_URL}api/find_user_in_crm/"
        data = {"phone_number": phone_number}
        async with session.post(url, json=data) as response:
            response_data: dict = await response.json()
            return response_data.get("user", None)


async def register_user_in_crm(message: Message, phone_number: str) -> dict | None:
    tg_user = message.from_user
    user_data = {
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name or "",
        "username": tg_user.username,
        "phone_number": phone_number,
    }
    async with aiohttp.ClientSession() as session:
        url = f"{DJANGO_API_URL}api/register_user_in_crm/"
        async with session.post(url, json=user_data) as response:
            response_data: dict = await response.json()
            return response_data.get("data", None)


async def create_or_update_clients_from_crm(db_user, crm_items: list) -> dict | None:
    """
    Отправляет данные на API для создания, обновления или удаления клиентов.
    """
    url = f"{DJANGO_API_URL}api/create_or_update_clients_in_db/"
    data = {
        "user_id": db_user["id"],
        "crm_items": crm_items,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                response_data: dict  = await response.json()

                if not response_data.get("success"):
                    logger.info(f"Ошибка при обновлении клиентов: {response_data.get('message')}")
                    return None
                else:
                    logger.info("Клиенты успешно обновлены в базе данных Django.")
                    return response_data
            else:
                error_message = (await response.json()).get("message", "Неизвестная ошибка")
                logger.error(f"Ошибка при обновлении клиентов: {error_message}")
                return None

# Клавиатура для клиентов
def get_client_keyboard():
    keyboard = [
        [KeyboardButton(text="Клиентская клавиатура")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# Клавиатура для Lead с группой
def get_lead_with_group_keyboard():
    keyboard = [
        [KeyboardButton(text="Клавиатура для Lead с группой")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


# Клавиатура для Lead
def get_lead_keyboard():
    keyboard = [
        [KeyboardButton(text="Клавиатура для Lead")],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
