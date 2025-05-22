from aiogram import Router, F, Dispatcher
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from tg_bot.keyboards.inline_keyboards.inline_keyboard_links_menu import links_menu_inline
from tg_bot.service.api_requests import get_social_links_from_api, get_user_tg_links_from_api

social_router = Router()


@social_router.callback_query(F.data == "menu_links")
async def menu_links(callback: CallbackQuery):
    await callback.message.answer("Где нас найти?", reply_markup=links_menu_inline)
    await callback.answer()






@social_router.callback_query(F.data == "social_links")
async def social_links_handler(callback: CallbackQuery):
    """
    Обработчик кнопки "Социальные ссылки".
    Отправляет список всех социальных ссылок.
    """
    links = await get_social_links_from_api()
    if not links:
        await callback.message.answer("Список социальных ссылок пуст.")
        await callback.answer()
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=link["name"], url=link["link"])]
            for link in links
        ]
        + [[InlineKeyboardButton(text="<< Назад", callback_data="inline_main_menu")]]
    )

    await callback.message.answer("Наши социальные сети:", reply_markup=keyboard)
    await callback.answer()



@social_router.callback_query(F.data == "tg_links")
async def tg_links_handler(callback: CallbackQuery):
    buttons = [
        InlineKeyboardButton(
            text="Главный новостной канал KIBERone", url="https://t.me/kiberone_bel"
        )
    ]

    user_id = callback.from_user.id
    links = await get_user_tg_links_from_api(user_id)

    if links:
        for link in links:
            if link.startswith("https://t.me/"):
                buttons.append(InlineKeyboardButton(text="Чат группы", url=str(link)))

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[button] for button in buttons],
        resize_keyboard=True,
        input_field_placeholder="Перейдите по ссылкам для вступления в группы..",
    )
    await callback.message.answer("Вот необходимые телеграм-ссылки:", reply_markup=keyboard)
    await callback.answer()