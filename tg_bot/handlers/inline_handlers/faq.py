from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from tg_bot.service.api_requests import get_all_questions, get_answer_by_question_id
from tg_bot.handlers.inline_handlers.main_menu import get_user_keyboard
from tg_bot.configs.bot_messages import FAQ_EMPTY, FAQ_SELECT, FAQ_ANSWER_NOT_FOUND

faq_router = Router()


@faq_router.callback_query(F.data == "faq")
async def faq_handler(callback: CallbackQuery):
    """
    Обработчик нажатия на кнопку FAQ.
    Отправляет список вопросов.
    """
    questions = await get_all_questions()
    if not questions:
        await callback.message.answer(FAQ_EMPTY)
        await callback.answer()  # Завершаем коллбэк
        return

    # Создаем клавиатуру с вопросами
    keyboard = InlineKeyboardBuilder()
    for question in questions:
        keyboard.button(
            text=question["question"], callback_data=f"faq_question_{question['id']}"
        )
    keyboard.button(text="<< Главное меню", callback_data="inline_main_menu")
    keyboard.adjust(1)

    await callback.message.edit_text(FAQ_SELECT, reply_markup=keyboard.as_markup())
    await callback.answer()  # Завершаем коллбэк


@faq_router.callback_query(F.data.startswith("faq_question_"))
async def handle_faq_question(callback: CallbackQuery):
    """
    Обработчик выбора вопроса.
    Отправляет ответ на выбранный вопрос.
    """
    question_id = callback.data.split("_")[-1]
    answer_data = await get_answer_by_question_id(question_id)
    if not answer_data:
        await callback.message.answer(FAQ_ANSWER_NOT_FOUND)
        return

    # Создаем клавиатуру с кнопкой "Назад"
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="<< Назад", callback_data="faq")
    keyboard.adjust(1)

    await callback.message.edit_text(
        f"<b>Вопрос:</b> {answer_data['question']}\n\n<b>Ответ:</b> {answer_data['answer']}",
        reply_markup=keyboard.as_markup(),
    )
    await callback.answer()
