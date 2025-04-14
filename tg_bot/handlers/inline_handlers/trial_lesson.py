from datetime import datetime
from aiogram import Router, F
from aiogram.types import CallbackQuery

from tg_bot.service.api_requests import find_user_in_django, get_location_info, get_user_trial_lessons
from tg_bot.configs.logger_config import get_logger

logger = get_logger()

trial_lesson_router = Router()


days_of_week = {
    "0": "Понедельник",
    "1": "Вторник",
    "2": "Среда",
    "3": "Четверг",
    "4": "Пятница",
    "5": "Суббота",
    "6": "Воскресенье",
}


@trial_lesson_router.callback_query(F.data == "user_trial_date")
async def user_trial_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Пробное занятие".
    """
    user_id = callback.from_user.id
    logger.debug(f"Начало обработки запроса на пробное занятие от пользователя с ID: {user_id}")

    try:
        await callback.message.answer("Ожидайте пожалуйста, проверяю Ваше расписание..")
        logger.debug(f"Сообщение пользователю с ID {user_id} изменено на 'Ожидайте...'")

        # Получаем данные пользователя из Django
        user_data = await find_user_in_django(user_id)
        if not user_data or not user_data.get("success"):
            await callback.message.answer(
                "Ошибка: не удалось получить данные пользователя."
            )
            await callback.answer()
            return

        user = user_data.get("user", {})
        clients = user.get("clients", [])

        if not clients:
            await callback.message.answer("У вас нет привязанных клиентов.")
            await callback.answer()
            return

        # Выбираем первого клиента (можно добавить выбор активного клиента)
        for client in clients:
            user_crm_id = client.get("crm_id")
            branch_id = client.get("branch_id")

            if not user_crm_id or not branch_id:
                await callback.message.answer(
                    "Ошибка: недостаточно данных для получения пробного занятия."
                )
                await callback.answer()
                return

            # Получаем пробные уроки
            lessons_data = await get_user_trial_lessons(user_crm_id, branch_id)
            if not lessons_data or lessons_data.get("total", 0) == 0:
                await callback.message.answer(
                    "У вас нет запланированных пробных занятий."
                )
                await callback.answer()
                return

            # Обрабатываем первый пробный урок
            trial_lesson = lessons_data.get("items", [])[0]
            lesson_date = trial_lesson.get("date")
            lesson_time_from = trial_lesson.get("time_from")
            lesson_time_to = trial_lesson.get("time_to")
            room_id = trial_lesson.get("room_id")

            # Форматируем дату и время
            lesson_datetime = datetime.strptime(lesson_date, "%Y-%m-%d")
            lesson_day = days_of_week[str(lesson_datetime.weekday())]
            lesson_time = f"{lesson_time_from.split(' ')[1][:-3]} - {lesson_time_to.split(' ')[1][:-3]}"

            # Получаем информацию о локации
            location_info = await get_location_info(room_id)
            if not location_info:
                lesson_address = "Адрес занятия неизвестен."
            else:
                location_name = location_info.get("name", "Без названия")
                location_map_link = location_info.get("map_url", "#")
                lesson_address = f"{location_name}\n{location_map_link}"

            await callback.message.answer(
                text=f"Вы записаны на пробное занятие:\n"
                f"{lesson_day}: {lesson_time}\n"
                f"Локация: {lesson_address}"
            )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при обработке запроса на пробное занятие: {e}")
        await callback.message.answer(
            "Произошла ошибка при обработке вашего запроса. Попробуйте позже."
        )
        await callback.answer()

    logger.debug(
        f"Завершение обработки запроса на пробное занятие от пользователя с ID: {user_id}"
    )
