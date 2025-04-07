
import asyncio
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from tg_bot.handlers import handler_start
from tg_bot.configs.set_commands import set_main_menu
from tg_bot.configs.logger_config import get_logger

logger = get_logger()
load_dotenv()

DEBUG = os.getenv('BOT_DEBUG') == 'True'

if DEBUG:
    BOT_TOKEN = os.environ.get("TEST_BOT_TOKEN")
else:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")


async def on_startup(bot: Bot):
    logger.info("Starting bot..")
    # await bot.send_message(chat_id="404331105", text="Bot started!")


async def on_shutdown(bot: Bot):
    logger.info("Processing shutdown..")

async def main():
    """
    Main function of the bot.

    Initialize bot and dispatcher, register startup and shutdown callbacks,
    include routers, delete webhook, set main menu, start polling and close bot session.

    :return: None
    """
    bot: Bot = Bot(
        token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp: Dispatcher = Dispatcher(storage=MemoryStorage())

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_routers (
        handler_start.start_router,
    )

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await set_main_menu(bot)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types(), timeout_seconds=30, polling_timeout=30)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
