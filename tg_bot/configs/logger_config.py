import logging
from dotenv import load_dotenv
import os

load_dotenv()

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL")

logging.basicConfig(
    level=logging.DEBUG if LOGGER_LEVEL == "DEBUG" else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("bot.log", mode="w")],
)
logger = logging.getLogger(__name__)


def get_logger():
    return logger
