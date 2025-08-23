import logging
import re
import json
from io import BytesIO

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command

import settings
from triggers import russian_swear_triggers
from app.statistics import bot_stats

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
bot = Bot(token=settings.token)
dp = Dispatcher()
commands_router = Router()  # Роутер для команд
triggers_router = Router()  # Роутер для триггеров

# Список администраторов по username
ADMIN_USERNAMES = ['dunda2', 'window_exit']

def is_admin(message: Message) -> bool:
    """Проверка, является ли пользователь администратором"""
    return message.from_user.username in ADMIN_USERNAMES


for word, reply in russian_swear_triggers.items():
    # генерим регулярку: игнор регистра, допускаем знаки вокруг
    pattern = re.compile(rf".*\b{word}\b$", re.IGNORECASE)

    async def handler(message: Message, reply=reply, trigger=word):
        # Записываем статистику
        bot_stats.add_roast(
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            trigger=trigger
        )
        await message.answer(reply)

    triggers_router.message(F.text.regexp(pattern))(handler)


# Команды статистики
@commands_router.message(Command("stats"))
async def show_stats(message: Message):
    """Показать общую статистику бота"""
    stats_text = bot_stats.get_stats_summary()
    await message.answer(stats_text)


@commands_router.message(Command("top"))
async def show_top_triggers(message: Message):
    """Показать топ триггеров"""
    top = bot_stats.get_top_triggers(10)
    if not top:
        await message.answer("📊 Пока нет статистики по триггерам")
        return

    text = "🏆 Топ-10 триггеров:\n\n"
    for i, (trigger, count) in enumerate(top.items(), 1):
        text += f"{i}. '{trigger}' - {count} раз\n"

    await message.answer(text)


@commands_router.message(Command("today"))
async def show_today_stats(message: Message):
    """Показать статистику за сегодня"""
    today = bot_stats.get_daily_stats()

    text = f"""📅 Статистика за сегодня ({today['date']})

🔥 Подъёбов: {today['roasts']}
👥 Пользователей: {today['unique_users']}
💬 Групп: {today['unique_groups']}"""

    await message.answer(text)


# Админские команды (скрыты от обычных пользователей)
@commands_router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    """Детальная статистика (только для админов)"""
    if not is_admin(message):
        # Не отвечаем обычным пользователям - скрываем команду
        return

    detailed_stats = bot_stats.get_detailed_stats()
    await message.answer(detailed_stats)


@commands_router.message(Command("export_stats"))
async def export_stats(message: Message):
    """Экспорт статистики в JSON файл (только для админов)"""
    if not is_admin(message):
        # Не отвечаем обычным пользователям - скрываем команду
        return

    try:
        stats_data = bot_stats.export_stats()
        json_data = json.dumps(stats_data, ensure_ascii=False, indent=2)

        # Создаем файл в памяти
        file_buffer = BytesIO(json_data.encode('utf-8'))
        input_file = BufferedInputFile(
            file_buffer.getvalue(),
            filename="bot_stats_export.json"
        )

        await message.answer_document(
            input_file,
            caption="📊 Экспорт статистики бота"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@commands_router.message(Command("clear_stats"))
async def clear_stats(message: Message):
    """Очистить статистику (только для админов)"""
    if not is_admin(message):
        # Не отвечаем обычным пользователям - скрываем команду
        return

    bot_stats.clear_stats()
    await message.answer("🗑️ Статистика очищена!\n\nВся статистика была сброшена до нуля.")


@commands_router.message(Command("help"))
async def show_help(message: Message):
    """Показать список команд (разный для админов и обычных пользователей)"""

    # Обычные команды для всех
    help_text = """🤖 Команды бота:

📊 Статистика:
/stats - общая статистика
/top - топ триггеров
/today - статистика за сегодня
/help - эта справка"""

    # Для админов добавляем админские команды
    if is_admin(message):
        help_text += """

👑 Админские команды:
/admin_stats - детальная статистика
/export_stats - экспорт в JSON
/clear_stats - очистить статистику"""

    help_text += "\n\nПросто пишите фразы, и я буду отвечать! 😄"

    await message.answer(help_text)


@commands_router.message(Command("start"))
async def start_command(message: Message):
    """Команда start для приветствия"""
    welcome_text = """👋 Добро пожаловать в PizdaBot!

Я отвечаю на различные фразы забавными ответами.

📋 Используйте /help чтобы посмотреть все команды.

Просто напишите что-нибудь и посмотрите что получится! 😄"""

    await message.answer(welcome_text)


async def main():
    # Подключаем роутеры в правильном порядке
    dp.include_router(commands_router)  # Команды первыми
    dp.include_router(triggers_router)  # Триггеры вторыми
    await dp.start_polling(bot)
