from aiogram import Router, F
from aiogram.types import CallbackQuery
from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from tg_bot.service.api_requests import get_erip_payment_help
from tg_bot.configs.logger_config import get_logger

logger = get_logger()
erip_router = Router()


@erip_router.callback_query(F.data == "erip_info")
async def process_button_erip_press(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку "Инструкция по оплате".
    Отправляет инструкцию по оплате через ЕРИП.
    """
    logger.debug(
        f"Получен запрос на обработку кнопки 'erip_payment' от пользователя {callback.from_user.id}"
    )

    # Получаем инструкцию из API
    help_data = await get_erip_payment_help()
    if not help_data:
        await callback.message.answer("Инструкция по оплате временно недоступна.")
        await callback.answer()
        return

    erip_link = help_data.get("erip_link", "")
    erip_instructions = help_data.get("erip_instructions", "")

    formatted_text = f"""
    <b>Инструкция по оплате через ЕРИП:</b>

    {erip_instructions}

    Для удобства вы можете перейти по ссылке: {erip_link}
    """

    try:
        await callback.message.answer(
            formatted_text, reply_markup=await get_user_keyboard(callback.from_user.id)
        )
        logger.info(
            f"Отправлено сообщение пользователю {callback.from_user.id} с инструкцией по оплате через ЕРИП."
        )
    except Exception as e:
        logger.error(f"Ошибка при отправке инструкции: {e}")
        await callback.message.answer("Произошла ошибка при отправке инструкции.")

    await callback.answer()
