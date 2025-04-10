import logging
from dotenv import load_dotenv
import os

load_dotenv()

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL")

logging.basicConfig(
    level=logging.DEBUG if LOGGER_LEVEL == "DEBUG" else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(lineno)d - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", mode="w", encoding='utf-8')],
)
logger = logging.getLogger(__name__)


def get_logger():
    return logger
