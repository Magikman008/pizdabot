from app.bot import dp, bot
from app.handlers import router
from app.services import scheduler_service


async def main():
    dp.include_router(router)

    # Запускаем планировщик задач
    await scheduler_service.start()

    try:
        # Запускаем polling бота
        await dp.start_polling(bot)
    finally:
        # Останавливаем планировщик при завершении
        await scheduler_service.stop()
