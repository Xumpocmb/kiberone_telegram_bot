from aiogram import Bot, Dispatcher, types
from aiogram.filters import BaseFilter
from dotenv import load_dotenv

import os

load_dotenv()

ADMIN_LIST = list(map(int, os.getenv("ADMIN_LIST").split(",")))

class IsAdmin(BaseFilter):
    async def __call__(self, message: types.Message) -> bool:
        """Check if the user is an admin.

        Args:
            message: The message containing the user.

        Returns:
            True if the user is an admin, False otherwise.
        """
        return message.from_user.id in ADMIN_LIST
