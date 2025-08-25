import re

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.user_triggers import user_trigger_manager
from app.utils.decorators import premium_only
from app.utils.tools import escape_markdown, is_admin

custom_triggers_router = Router()

@custom_triggers_router.message(Command("add"))
@premium_only
async def add_trigger(message: Message):
    """Добавить пользовательский триггер (ТОЛЬКО для подписчиков)"""
    if not message.text:
        return

    # ДЛЯ ПРЕМИУМ-ПОЛЬЗОВАТЕЛЕЙ УБИРАЕМ ВСЕ ЛИМИТЫ
    user_trigger_manager.MAX_TRIGGERS_PER_USER_PER_DAY = 999999  # Безлимит
    user_trigger_manager.MAX_TRIGGERS_PER_CHAT = 999999  # Безлимит

    # Парсим команду с помощью регулярного выражения для извлечения "фраза" "ответ"
    pattern = r'/add\s+"([^"]+)"\s+"([^"]+)"'
    match = re.match(pattern, message.text)

    if not match:
        await message.answer(
            "❌ *Неправильный формат команды\\!*\n\n"
            'Используйте: `/add "фраза" "ответ"`\n'
            'Пример: `/add "привет" "и тебе привет!"`',
            parse_mode="MarkdownV2",
        )
        return

    trigger, response = match.groups()

    success, msg = user_trigger_manager.add_trigger(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        trigger=trigger,
        response=response,
    )

    # Добавляем информацию о премиум-статусе
    if success:
        msg += "\n\n⭐ *Премиум-пользователь:* безлимитное добавление триггеров!"

    escaped_msg = escape_markdown(msg)
    await message.answer(escaped_msg, parse_mode="MarkdownV2")


@custom_triggers_router.message(Command("remove"))
async def remove_trigger(message: Message):
    """Удалить пользовательский триггер"""
    if not message.text:
        return

    # Парсим команду для извлечения "фраза"
    pattern = r'/remove\s+"([^"]+)"'
    match = re.match(pattern, message.text)

    if not match:
        await message.answer(
            "❌ *Неправильный формат команды\\!*\n\n"
            'Используйте: `/remove "фраза"`\n'
            'Пример: `/remove "привет"`',
            parse_mode="MarkdownV2",
        )
        return

    trigger = match.groups()[0]

    success, msg = user_trigger_manager.remove_trigger(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        trigger=trigger,
        is_admin=is_admin(message),
    )

    escaped_msg = escape_markdown(msg)
    await message.answer(escaped_msg, parse_mode="MarkdownV2")


@custom_triggers_router.message(Command("triggers"))
async def list_triggers(message: Message):
    """Показать все триггеры чата"""
    triggers_list = user_trigger_manager.list_chat_triggers(message.chat.id)
    escaped_list = escape_markdown(triggers_list)
    await message.answer(escaped_list, parse_mode="MarkdownV2")


@custom_triggers_router.message(Command("my_triggers"))
@premium_only
async def my_triggers_stats(message: Message):
    """Показать статистику пользователя по триггерам"""
    stats = user_trigger_manager.get_user_stats(message.from_user.id)

    # Добавляем информацию о премиум-статусе
    stats += "\n\n⭐ *Премиум-статус активен!*\n• Безлимитное добавление триггеров\n• Приоритетная обработка"

    escaped_stats = escape_markdown(stats)
    await message.answer(escaped_stats, parse_mode="MarkdownV2")
