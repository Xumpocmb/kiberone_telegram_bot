from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

button_1: InlineKeyboardButton = InlineKeyboardButton(
    text='Ссылки на соц. сети',
    callback_data='social_links')



button_2: InlineKeyboardButton = InlineKeyboardButton(
    text='<< Главное меню',
    callback_data='inline_main_menu')

# button_3: InlineKeyboardButton = InlineKeyboardButton(
#     text='Ссылки на телеграм',
#     callback_data='tg_links')


links_menu_inline: InlineKeyboardMarkup = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            button_1
        ],[
            button_2
        ],
    ]
)
