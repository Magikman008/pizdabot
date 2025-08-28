from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers import bot_stats, subscription_manager
from app.utils.decorators import admin_only
from app.utils.tools import escape_markdown

admin_router = Router()


@admin_router.message(Command("admin_stats"))
@admin_only
async def admin_stats(message: Message):
    """Детальная статистика (только для админов)"""
    detailed_stats = bot_stats.get_admin_stats()

    # Добавляем информацию о подписчиках
    subscribers = subscription_manager.get_all_subscribers()
    detailed_stats += f"\n\n⭐ Активных подписчиков: {len(subscribers)}"

    escaped_stats = escape_markdown(detailed_stats)
    await message.answer(escaped_stats, parse_mode="MarkdownV2")


@admin_router.message(Command("subscribers"))
@admin_only
async def show_subscribers(message: Message):
    """Показать список подписчиков (только для админов)"""
    subscribers = subscription_manager.get_all_subscribers()

    if not subscribers:
        await message.answer("📋 Активных подписчиков нет", parse_mode="MarkdownV2")
        return

    text = f"👥 *Активные подписчики ({len(subscribers)}):*\n\n"

    for i, (tg_chat_id, sub) in enumerate(subscribers.items(), 1):
        expires_at = sub.expires_at
        if isinstance(expires_at, datetime):
            expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M")
        else:
            expires_at_str = str(expires_at)[:16]  # на всякий случай

        escaped_expires = expires_at_str
        text += f"{i}. ID: {tg_chat_id} (до {escaped_expires})\n"

    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
