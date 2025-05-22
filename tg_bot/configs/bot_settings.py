import os

from dotenv import load_dotenv


load_dotenv()

DEBUG = os.getenv('BOT_DEBUG') == 'True'

if DEBUG:
    BOT_TOKEN = os.environ.get("TEST_BOT_TOKEN")
else:
    BOT_TOKEN = os.environ.get("BOT_TOKEN")

if DEBUG:
    API_URL = os.getenv("LOCAL_KIBER_API_URL")
else:
    API_URL = os.getenv("KIBER_API_URL")