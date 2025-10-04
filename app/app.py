from app.bot import dp, bot
from app.handlers import router


async def main():
    dp.include_router(router)

    await dp.start_polling(bot)
