import os

from aiogram import F
from aiogram import Router
from aiogram.types import CallbackQuery, FSInputFile
from tg_bot.configs.logger_config import get_logger

logger = get_logger()

english_platform_router: Router = Router()


@english_platform_router.callback_query(F.data == 'english_platform')
async def process_button_english_press(callback: CallbackQuery):
    logger.debug("Обработка нажатия кнопки 'english_platform'")
    logger.debug(f"Получен запрос от пользователя: {callback.from_user.id}")

    response_text = (
        'Lim English – это набор курсов для обучения английскому языку. '
        'Все курсы делятся по уровню сложности и тематике. '
        'Каждый урок может содержать в себе видео, аудирование, словарь, диктант и перевод.\n'
        'Для наших резидентов платформа доступна в виде приятного бонуса!\n'
        'Ниже инструкцию по работе и доступом.\n'
        'P.S. ОЧЕНЬ ПРОСИМ ВАС НЕ ИЗМЕНЯТЬ ПАРОЛЬ И ИСПОЛЬЗОВАТЬ ТОЛЬКО ТОТ, КОТОРЫЙ ПРЕДОСТАВЛЕН В ИНСТРУКЦИИ!!! 🤗\n'
    )

    try:
        await callback.message.answer(text=response_text)
        logger.info(f"Отправлено сообщение пользователю {callback.from_user.id}: {response_text}")
        filename = os.path.abspath("tg_bot/files/Lim_English.pdf")
        document = FSInputFile(filename)
        await callback.message.answer_document(document=document, caption='Инструкция по работе с платформой')
        logger.info(f"Отправлен документ пользователю {callback.from_user.id}: LimEnglish.pdf")

        await callback.answer()
        logger.debug(f"Подтверждение нажатия кнопки отправлено пользователю {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при обработке нажатия кнопки 'english_platform': {e}")
