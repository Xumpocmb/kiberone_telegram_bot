# -----------------------------------------------------------

# ОТПРАВКА ЗАПРОСОВ НА АПИ

# -----------------------------------------------------------

import os
import aiohttp
from tg_bot.configs.logger_config import get_logger
from aiogram.types import Message

logger = get_logger()
DJANGO_API_URL = os.getenv("KIBER_API_URL")


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
                        logger.info(f"Пользователь найден в БД")
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


async def register_user_in_db(
    telegram_id: int, username: str, phone_number: str
) -> dict | None:
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
                response_data: dict = await response.json()

                if not response_data.get("success"):
                    logger.info(
                        f"Ошибка при обновлении клиентов: {response_data.get('message')}"
                    )
                    return None
                else:
                    logger.info("Клиенты успешно обновлены в базе данных Django.")
                    return response_data
            else:
                error_message = (await response.json()).get(
                    "message", "Неизвестная ошибка"
                )
                logger.error(f"Ошибка при обновлении клиентов: {error_message}")
                return None
