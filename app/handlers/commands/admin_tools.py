import json
from io import BytesIO

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from app.statistics import bot_stats
from app.subscription_manager import subscription_manager
from app.user_triggers import user_trigger_manager
from app.utils.decorators import admin_only
from app.utils.tools import escape_markdown

admin_router = Router()


@admin_router.message(Command("admin_stats"))
@admin_only
async def admin_stats(message: Message):
    """Детальная статистика (только для админов)"""
    detailed_stats = bot_stats.get_detailed_stats()

    # Добавляем информацию о подписчиках
    subscribers = subscription_manager.get_all_subscribers()
    detailed_stats += f"\n\n⭐ Активных подписчиков: {len(subscribers)}"

    escaped_stats = escape_markdown(detailed_stats)
    await message.answer(escaped_stats, parse_mode="MarkdownV2")


@admin_router.message(Command("export_stats"))
@admin_only
async def export_stats(message: Message):
    """Экспорт статистики в JSON файл (только для админов)"""
    try:
        stats_data = bot_stats.export_stats()
        json_data = json.dumps(stats_data, ensure_ascii=False, indent=2)

        # Создаем файл в памяти
        file_buffer = BytesIO(json_data.encode("utf-8"))
        input_file = BufferedInputFile(
            file_buffer.getvalue(), filename="bot_stats_export.json"
        )

        await message.answer_document(input_file, caption="📊 Экспорт статистики бота")
    except Exception as e:
        escaped_error = escape_markdown(str(e))
        await message.answer(
            f"❌ Ошибка при экспорте: {escaped_error}", parse_mode="MarkdownV2"
        )


@admin_router.message(Command("clear_stats"))
@admin_only
async def clear_stats(message: Message):
    """Очистить статистику (только для админов)"""
    bot_stats.clear_stats()
    await message.answer(
        "🗑️ *Статистика очищена\\!*\n\nВся статистика была сброшена до нуля\\.",
        parse_mode="MarkdownV2",
    )


@admin_router.message(Command("remove_all_triggers"))
@admin_only
async def remove_all_triggers(message: Message):
    """Удалить все пользовательские триггеры чата (только для админов)"""
    chat_str = str(message.chat.id)
    if chat_str in user_trigger_manager.data["chat_triggers"]:
        user_trigger_manager.data["chat_triggers"][chat_str] = {}
        user_trigger_manager._save_triggers()
        await message.answer(
            "🗑️ Все пользовательские триггеры чата удалены\\!", parse_mode="MarkdownV2"
        )
    else:
        await message.answer(
            "❌ В этом чате нет пользовательских триггеров", parse_mode="MarkdownV2"
        )


@admin_router.message(Command("subscribers"))
@admin_only
async def show_subscribers(message: Message):
    """Показать список подписчиков (только для админов)"""
    subscribers = subscription_manager.get_all_subscribers()

    if not subscribers:
        await message.answer("📋 Активных подписчиков нет", parse_mode="MarkdownV2")
        return

    text = f"👥 *Активные подписчики \\({len(subscribers)}\\):*\n\n"

    for i, (user_str, sub_data) in enumerate(subscribers.items(), 1):
        expires_at = sub_data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = expires_at[:16]  # Обрезаем до даты и времени
        escaped_expires = escape_markdown(expires_at)
        text += f"{i}\\. ID: {user_str} \\(до {escaped_expires}\\)\n"

    await message.answer(text, parse_mode="MarkdownV2")
