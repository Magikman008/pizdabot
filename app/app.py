import logging

# from Tools.i18n.pygettext import escape_ascii
from aiogram import Bot, Dispatcher

import settings
from app.handlers import router
from app.subscription_manager import subscription_manager

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
bot = Bot(token=settings.token)
dp = Dispatcher()

# Список администраторов по username


async def main():
    dp.include_router(router)

    # Очищаем истёкшие подписки при запуске
    subscription_manager.cleanup_expired_subscriptions()

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
