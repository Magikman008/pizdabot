# from Tools.i18n.pygettext import escape_ascii
from app.bot import dp, bot
from app.controllers import subscription_manager
from app.handlers import router




async def main():
    dp.include_router(router)

    # Очищаем истёкшие подписки при запуске
    subscription_manager.cleanup_expired_subscriptions()

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
