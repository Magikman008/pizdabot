from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.chat_settings import chat_settings_manager
from app.utils.decorators import admin_only
from app.utils.tools import escape_markdown

chat_settings_router = Router()


@chat_settings_router.message(Command("off"))
async def turn_bot_off(message: Message):
    """Выключить бота в чате"""
    success, msg = chat_settings_manager.set_bot_enabled(
        chat_id=message.chat.id, enabled=False, user_id=message.from_user.id
    )
    escaped_msg = escape_markdown(msg)
    await message.answer(escaped_msg, parse_mode="MarkdownV2")


@chat_settings_router.message(Command("on"))
async def turn_bot_on(message: Message):
    """Включить бота в чате"""
    success, msg = chat_settings_manager.set_bot_enabled(
        chat_id=message.chat.id, enabled=True, user_id=message.from_user.id
    )
    escaped_msg = escape_markdown(msg)
    await message.answer(escaped_msg, parse_mode="MarkdownV2")


@chat_settings_router.message(Command("chance"))
async def set_response_chance(message: Message):
    """Установить вероятность ответа бота"""
    if not message.text:
        return

    # Парсим команду для извлечения числа
    pattern = r"/chance\s+(\d+)"
    match = re.match(pattern, message.text)

    if not match:
        await message.answer(
            "❌ *Неправильный формат команды\\!*\n\n"
            "Используйте: `/chance <число от 0 до 100>`\n"
            "*Примеры:*\n"
            "`/chance 50` \\- бот отвечает в 50% случаев\n"
            "`/chance 0` \\- бот не отвечает\n"
            "`/chance 100` \\- бот отвечает всегда",
            parse_mode="MarkdownV2",
        )
        return

    try:
        chance = int(match.group(1))
    except ValueError:
        await message.answer(
            "❌ Введите корректное число от 0 до 100\\!", parse_mode="MarkdownV2"
        )
        return

    success, msg = chat_settings_manager.set_response_chance(
        chat_id=message.chat.id, chance=chance, user_id=message.from_user.id
    )
    escaped_msg = escape_markdown(msg)
    await message.answer(escaped_msg, parse_mode="MarkdownV2")


@chat_settings_router.message(Command("settings"))
async def show_chat_settings(message: Message):
    """Показать текущие настройки чата"""
    settings_info = chat_settings_manager.get_chat_info(message.chat.id)
    escaped_info = escape_markdown(settings_info)
    await message.answer(escaped_info, parse_mode="MarkdownV2")


@chat_settings_router.message(Command("reset_settings"))
@admin_only
async def reset_chat_settings(message: Message):
    """Сбросить настройки чата (только админы)"""
    success, msg = chat_settings_manager.reset_chat_settings(
        chat_id=message.chat.id, user_id=message.from_user.id
    )
    escaped_msg = escape_markdown(msg)
    await message.answer(escaped_msg, parse_mode="MarkdownV2")
