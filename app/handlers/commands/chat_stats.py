from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers import bot_stats
from app.utils.tools import escape_markdown

chat_stats_router = Router()


@chat_stats_router.message(Command("stats"))
async def show_stats(message: Message):
    """Показать общую статистику бота"""
    stats_text = bot_stats.get_stats_summary()
    escaped_stats = escape_markdown(stats_text)
    await message.answer(escaped_stats, parse_mode="MarkdownV2")


@chat_stats_router.message(Command("top"))
async def show_top_triggers(message: Message):
    """Показать топ триггеров"""
    top = bot_stats.get_top_triggers(10)
    if not top:
        await message.answer(
            "📊 Пока нет статистики по триггерам", parse_mode="MarkdownV2"
        )
        return

    text = "🏆 *Топ-10 триггеров:*\n\n"
    for i, (trigger, count) in enumerate(top.items(), 1):
        text += f"{i}. '{trigger}' - {count} раз"

    escaped_text = escape_markdown(text)
    await message.answer(escaped_text, parse_mode="MarkdownV2")


@chat_stats_router.message(Command("today"))
async def show_today_stats(message: Message):
    """Показать статистику за сегодня"""
    today = bot_stats.get_daily_stats()

    text = f"""📅 *Статистика за сегодня* \\({escape_markdown(today['date'])}\\)

🔥 Подъёбов: {today['roasts']}
👥 Пользователей: {today['unique_users']}
💬 Групп: {today['unique_groups']}"""

    await message.answer(text, parse_mode="MarkdownV2")
