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
CRM_API_URL = "http://localhost:8000/api_crm/"


#-----------------------------------------------------------

# ХЕНДЛЕРЫ СТАРТ

#-----------------------------------------------------------

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
    # greeting = f"Привет, {message.from_user.username}!\n{formatted_message}"
    # logger.debug("Запрашиваю у пользователя контакт..")
    # filename = "files/contact_image.png"
    # file = types.FSInputFile(filename)
    # contact_keyboard = ReplyKeyboardMarkup(
    #     resize_keyboard=True,
    #     keyboard=[[KeyboardButton(text="Поделиться контактом", request_contact=True)]]
    # )
    # await message.answer(greeting, reply_markup=contact_keyboard)
    # await message.answer_photo(file, caption="Поделитесь своим контактом с KIBERone")
    await message.answer(DJANGO_API_URL)


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
    tg_user = message.from_user
    telegram_id = message.contact.user_id
    username = message.from_user.username
    phone_number = str(re.sub(r'\D', '', message.contact.phone_number))

    # Поиск в БД Django
    db_user = await find_user_in_django(telegram_id)
    if not db_user:
        await message.answer("Вы не зарегистрированы в боте!")
        registration_result = await register_user_in_db(telegram_id, username, phone_number)
        if registration_result and registration_result.get("success"):
            db_user = registration_result.get("user")
            await message.answer("Вы успешно зарегистрированы в системе Django!\nДавайте проверим нашу ЦРМ...")
        else:
            await message.answer(f"Ошибка регистрации в системе: {registration_result.get('error')}")
            return

    # Убедитесь, что db_user содержит id
    if not isinstance(db_user, dict) or "id" not in db_user:
        await message.answer("Ошибка: некорректные данные пользователя.")
        return

    # Поиск в CRM
    await handle_crm_lookup(message, phone_number, db_user)

    # Получаем актуальный статус пользователя
    updated_db_user = await find_user_in_django(telegram_id)
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

#-----------------------------------------------------------

# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ОБРАБОТКИ ИНФОРМАЦИИ

#-----------------------------------------------------------

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


# Поиск в црм
async def handle_crm_lookup(message: Message, phone_number: str, db_user: dict):
    try:
        logger.info(f"Поиск пользователя в CRM по номеру телефона: {phone_number}")
        crm_response = await find_user_in_crm(phone_number)
        if not crm_response or not crm_response.get("found"):
            logger.warning(f"Пользователь с телефоном {phone_number} не найден в CRM.")
            await message.answer("Вы не зарегистрированы в CRM.\nРегистрируем...")
            register_response = await register_user_in_crm_handler(message, phone_number)
            crm_items = parse_crm_response(register_response)

            logger.info("Обновление пользователя в БД после регистрации в црм")
            response_data = await create_or_update_clients_from_crm(db_user, crm_items)
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

        await message.answer(
            "Вы уже зарегистрированы в CRM!\nДавайте проверим нашу систему на актуальность данных..."
        )

        result = crm_response.get("result", {})
        total_clients = result.get("total", 0)
        items = result.get("items", [])

        if total_clients == 0:
            await message.answer("В CRM нет клиентов для этого пользователя.")
        else:
            response_data = await create_or_update_clients_from_crm(db_user, items)
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

    except Exception as e:
        logger.error(f"Ошибка при работе с CRM: {str(e)}")
        await message.answer("Произошла ошибка при проверке данных в CRM.")


# Регистрация в CRM
async def register_user_in_crm_handler(message: Message, phone_number: str):
    tg_user = message.from_user
    user_data = {
        "first_name": tg_user.first_name or "",
        "last_name": tg_user.last_name or "",
        "username": tg_user.username,
        "phone_number": phone_number,
    }

    try:
        crm_register_response = await register_user_in_crm(user_data)
        if crm_register_response:
            await message.answer("Вы успешно зарегистрированы в CRM!")
            return crm_register_response
        else:
            error_message = crm_register_response.text or "Неизвестная ошибка"
            logger.error(f"Ошибка регистрации в CRM: {error_message}")
            await message.answer(f"Ошибка регистрации в CRM: {error_message}")
    except Exception as e:
        logger.error(f"Не удалось выполнить запрос к CRM: {str(e)}")
        await message.answer("Произошла ошибка при регистрации в CRM.")


def parse_crm_response(register_response):
    """
    Преобразует ответ от CRM в список словарей.
    """
    data = register_response.get("data", [])
    crm_items = []

    # Объединяем все строки в одну
    full_json_str = "".join(data)

    try:
        # Разбиваем объединенную строку на отдельные JSON-объекты
        items = json.loads(f"[{full_json_str}]")  # Добавляем квадратные скобки для создания списка
        for item in items:
            model_data = item.get("model")
            if model_data:
                crm_items.append(model_data)
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка при декодировании JSON: {e}")

    return crm_items


#-----------------------------------------------------------

# ОТПРАВКА ЗАПРОСОВ НА АПИ

#-----------------------------------------------------------

async def find_user_in_django(telegram_id):
    try:
        async with aiohttp.ClientSession() as session:
            data = {"telegram_id": telegram_id}
            async with session.post(
                    f"{DJANGO_API_URL}find_user/", json=data
            ) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("found"):
                        return response_data.get("user")
                    else:
                        logger.info(
                            f"Пользователь с telegram_id {telegram_id} не найден в БД."
                        )
                        return None
                else:
                    logger.error(
                        f"Ошибка при поиске пользователя в БД: {await response.json()}"
                    )
                    return None
    except Exception as e:
        logger.error(f"Не удалось выполнить запрос к БД: {e}")
        return None


async def register_user_in_db(telegram_id: int, username: str, phone_number: str) -> dict | None:
    """
    Регистрация нового пользователя в базе данных Django через API.
    """
    url = f"{DJANGO_API_URL}register_user/"
    data = {
        "telegram_id": str(telegram_id),
        "username": username,
        "phone_number": phone_number,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                if response.status == 201 or response.status == 200:
                    response_data = await response.json()
                    return response_data
                else:
                    error_message = await response.text()
                    logger.error(f"Ошибка регистрации пользователя: {error_message}")
                    return {"success": False, "error": error_message}
    except Exception as e:
        logger.error(f"Не удалось выполнить запрос к Django: {e}")
        return {"success": False, "error": str(e)}


async def find_user_in_crm(phone_number):
    """
    Поиск пользователя в CRM. Функция посредник, для вызова API.

    Args:
        phone_number (str): Номер телефона пользователя.

    Returns:
        dict: Словарь с информацией о пользователе.
    """
    async with aiohttp.ClientSession() as session:
        url = f"{CRM_API_URL}find_user/"
        data = {"phone_number": phone_number}
        async with session.post(url, json=data) as response:
            response_data = await response.json()
            return response_data


async def register_user_in_crm(user_data):
    async with aiohttp.ClientSession() as session:
        url = f"{CRM_API_URL}register_user/"
        async with session.post(url, json=user_data) as response:
            response_data = await response.json()
            return response_data


async def create_or_update_clients_from_crm(db_user, crm_items: list):
    """
    Отправляет данные на API для создания, обновления или удаления клиентов.
    """
    url = f"{DJANGO_API_URL}create_or_update_clients/"
    data = {
        "user_id": db_user["id"],
        "crm_items": crm_items,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data) as response:
            if response.status == 200:
                response_data = await response.json()
                logger.info(f"API ответ: {response_data}")
                return response_data
            else:
                error_message = await response.text()
                logger.error(f"Ошибка при вызове API: {error_message}")
                return None
