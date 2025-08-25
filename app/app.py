from app.bot import dp, bot
from app.controllers import subscription_manager
from app.db import init_db
from app.handlers import router


async def main():
    init_db()

    dp.include_router(router)

    # Очищаем истёкшие подписки при запуске
    subscription_manager.cleanup_expired_subscriptions()

    await dp.start_polling(bot)
