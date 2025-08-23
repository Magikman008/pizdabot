import logging
import re

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message

import settings
from triggers import russian_swear_triggers

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
bot = Bot(token=settings.token)
dp = Dispatcher()
start_router = Router()


for word, reply in russian_swear_triggers.items():
    # генерим регулярку: игнор регистра, допускаем знаки вокруг
    pattern = re.compile(rf"^\W*{word}\W*$", re.IGNORECASE)

    async def handler(message: Message, reply=reply):
        await message.answer(reply)

    start_router.message(F.text.regexp(pattern))(handler)

async def main():
    dp.include_router(start_router)
    await dp.start_polling(bot)
