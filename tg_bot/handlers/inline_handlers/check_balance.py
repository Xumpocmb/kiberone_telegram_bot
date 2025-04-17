from aiogram import Router, F
from aiogram import Router, F
from aiogram.types import CallbackQuery

from tg_bot.service.api_requests import get_user_balances_from_api

balance_router = Router()


@balance_router.callback_query(F.data == "check_balance")
async def check_balance_handler(callback: CallbackQuery):
    """
    Отправляет балансы всех клиентов пользователя.
    """
    telegram_id = callback.from_user.id

    # Уведомляем пользователя о начале проверки баланса
    await callback.message.answer("⏳ Проверяю балансы ваших клиентов...")

    # Получаем балансы клиентов через API
    balances = await get_user_balances_from_api(telegram_id)
    if not balances:
        await callback.message.answer("❌ Не удалось получить информацию о балансах.")
        await callback.answer()
        return

    # Если балансы пустые
    if not balances:
        await callback.message.answer("⚠️ У вас нет клиентов с балансом.")
        await callback.answer()
        return

    # Формируем текст сообщения с балансами
    balance_message = "📊 <b>Балансы ваших клиентов:</b>\n\n"
    for client in balances:
        client_name = client.get("client_name", "👤 Без имени")
        balance = client.get("balance", 0.0)
        balance_message += f"• {client_name}: <b>{balance:.2f} ₽</b>\n"

    # Отправляем сообщение с балансами
    await callback.message.answer(balance_message, parse_mode="HTML")
    await callback.answer("✅ Балансы успешно проверены!")
