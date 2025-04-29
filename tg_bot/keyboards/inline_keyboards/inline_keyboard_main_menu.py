import os

from dotenv import load_dotenv

load_dotenv()

KIBER_CLUB_URL = os.getenv("KIBER_CLUB_URL")

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

button_1: InlineKeyboardButton = InlineKeyboardButton(text="Вопрос & Ответ", callback_data="faq")
button_2: InlineKeyboardButton = InlineKeyboardButton(text="Оплатить", callback_data="erip_payment")
button_4: InlineKeyboardButton = InlineKeyboardButton(text="Платформа английского Lim English",
                                                      callback_data="english_platform")
button_5: InlineKeyboardButton = InlineKeyboardButton(text="Бонусы для клиентов", callback_data="client_bonuses")
button_6: InlineKeyboardButton = InlineKeyboardButton(text="Наши Партнёры", callback_data="partners_list")
button_7: InlineKeyboardButton = InlineKeyboardButton(text="Ваш менеджер KIBERone", callback_data="contact_manager")
button_8: InlineKeyboardButton = InlineKeyboardButton(text="Будь в тренде! (Inst, Tg)", callback_data="social_links")
button_9: InlineKeyboardButton = InlineKeyboardButton(text="Ссылки на телеграм чаты", callback_data="tg_links")
button_10: InlineKeyboardButton = InlineKeyboardButton(text="Наши Партнёры", callback_data="partner_without_promocodes")
button_12: InlineKeyboardButton = InlineKeyboardButton(text="Расписание занятий", callback_data="user_scheduler")
button_13: InlineKeyboardButton = InlineKeyboardButton(text="Дата пробного занятия", callback_data="user_trial_date")
button_14: InlineKeyboardButton = InlineKeyboardButton(text="Главный новостной канал KIBERone",
                                                       url="https://t.me/kiberone_bel")
button_15: InlineKeyboardButton = InlineKeyboardButton(text="Баланс", callback_data="check_balance")

button_16: InlineKeyboardButton = InlineKeyboardButton(
    text="Личный кабинет KIBERhub",
    web_app=WebAppInfo(
        # url=f"https://{os.getenv('NGROK') if os.getenv('DEBUG_WEB_APP') == 'True' else os.getenv('DOMAIN')}/kiberclub/index/"
        url=f"https://www.google.by/?hl=ru"))
button_17: InlineKeyboardButton = InlineKeyboardButton(text="Оплатить через ЕРИП", callback_data="erip_info")


def get_client_keyboard(user_tg_id) -> InlineKeyboardMarkup:
    """
    Возвращает InlineKeyboardMarkup для клиентов.
    """
    buttons = [
        [create_inline_button(text="Личный кабинет KIBERhub", web_app_url=f"{KIBER_CLUB_URL}index/?user_tg_id={user_tg_id}")],
        [
            create_inline_button(text="Баланс", callback_data="check_balance"),
            create_inline_button(text="Оплатить", callback_data="erip_payment")
        ],
        [create_inline_button(text="Бонусы для клиентов", callback_data="client_bonuses")],
        [create_inline_button(text="Ваш менеджер KIBERone", callback_data="contact_manager")],
        [create_inline_button(text="Будь в тренде! (Inst, Tg)", callback_data="social_links")],
        [create_inline_button(text="Вопрос & Ответ", callback_data="faq")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_lead_with_group_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для лидов с группой.
    """
    buttons = [
        [
            create_inline_button(text="Баланс", callback_data="check_balance"),
            create_inline_button(text="Оплатить", callback_data="erip_payment")
        ],
        [create_inline_button(text="Бонусы для клиентов", callback_data="client_bonuses")],
        [create_inline_button(text="Ваш менеджер KIBERone", callback_data="contact_manager")],
        [create_inline_button(text="Будь в тренде! (Inst, Tg)", callback_data="social_links")],
        [create_inline_button(text="Вопрос & Ответ", callback_data="faq")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_lead_without_group_keyboard() -> InlineKeyboardMarkup:
    """
    Возвращает клавиатуру для лидов без группы.
    """
    buttons = [
        [create_inline_button(text="Вопрос & Ответ", callback_data="faq")],
        [create_inline_button(text="Оплатить через ЕРИП", callback_data="erip_info")],
        [create_inline_button(text="Бонусы для клиентов", callback_data="client_bonuses")],
        [create_inline_button(text="Ваш менеджер KIBERone", callback_data="contact_manager")],
        [create_inline_button(text="Будь в тренде! (Inst, Tg)", callback_data="social_links")],
        [create_inline_button(text="Дата пробного занятия", callback_data="user_trial_date")],
        [create_inline_button(
            text="Главный новостной канал KIBERone",
            url="https://t.me/kiberone_bel"
        )],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def create_inline_button(
    text: str,
    callback_data: str = None,
    url: str = None,
    web_app_url: str = None
) -> InlineKeyboardButton:
    """
    Создает кнопку InlineKeyboardButton с указанными параметрами.
    """
    if web_app_url:
        return InlineKeyboardButton(
            text=text,
            web_app=WebAppInfo(url=web_app_url)
        )
    elif url:
        return InlineKeyboardButton(text=text, url=url)
    else:
        return InlineKeyboardButton(text=text, callback_data=callback_data)
