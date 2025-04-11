from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from tg_bot.service.api_requests import get_social_links_from_api

social_router = Router()


@social_router.callback_query(F.data == "social_links")
async def social_links_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Социальные ссылки".
    Отправляет список всех социальных ссылок.
    """
    # Получаем список социальных ссылок
    links = await get_social_links_from_api()
    if not links:
        await callback.message.answer("Список социальных ссылок пуст.")
        await callback.answer()
        return

    # Создаем клавиатуру с ссылками
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=link["name"], url=link["link"])]
            for link in links
        ]
        + [[InlineKeyboardButton(text="<< Назад", callback_data="inline_main_menu")]]
    )

    await callback.message.answer("Наши социальные сети:", reply_markup=keyboard)
    await callback.answer()
