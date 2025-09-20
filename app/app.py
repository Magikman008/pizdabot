from app.bot import dp, bot
from app.db import init_db
from app.handlers import router


async def main():
    init_db()

    dp.include_router(router)

    await dp.start_polling(bot)
