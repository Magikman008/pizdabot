from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.utils.tools import escape_markdown, is_admin

help_router = Router()


@help_router.message(Command("help"))
async def show_help(message: Message):
    help_text = (
        "🤖 *Команды бота Подъёбыш:*\n\n"
        "⚙️ *Управление ботом:*\n"
        "/on – включить бота в чате\n"
        "/off – выключить бота в чате\n"
        "/chance <0–100> – вероятность ответа (%)\n"
        "/settings – текущие настройки чата\n\n"
        "⭐ *Подписка:*\n"
        "/sub – купить премиум-подписку за 1 звёздочку\n"
        "/premium – премиум-функции (только для подписчиков)\n\n"
        "📊 *Статистика:*\n"
        "/stats – общая статистика\n"
        "/top – топ триггеров\n"
        "/today – статистика за сегодня\n\n"
        "🎯 *Пользовательские триггеры (ТОЛЬКО подписчики):*\n"
        '/add "фраза" "ответ" – добавить триггер (безлимитно)\n'
        '/remove "фраза" – удалить свой триггер\n'
        "/triggers – список триггеров чата\n"
        "/my_triggers – ваша статистика\n\n"
        "/help – эта справка"
    )
    if is_admin(message):
        help_text += (
            "\n\n👑 *Админские команды:*\n"
            "/admin_stats – детальная статистика\n"
            "/export_stats – экспорт статистики в JSON\n"
            "/clear_stats – очистить статистику\n"
            "/remove_all_triggers – удалить все триггеры чата\n"
            "/reset_settings – сбросить настройки чата\n"
            "/subscribers – список подписчиков"
        )
    escape_msg = escape_markdown(help_text)
    await message.answer(escape_msg, parse_mode="MarkdownV2")


@help_router.message(Command("start"))
async def start_command(message: Message):
    """Команда start для приветствия"""
    welcome_text = """👋 *Добро пожаловать в Подъёбыш\\!*

Я отвечаю на различные фразы забавными ответами\\.

🎯 *Премиум\\-подписка за звёздочки:*
/sub \\- купить подписку
• *Добавление пользовательских триггеров*
• *Безлимитное количество триггеров*
• Эксклюзивные функции
• Приоритетная обработка

⚠️ *Без подписки нельзя добавлять триггеры\\!*

⚙️ *Управляйте ботом:*
/off \\- выключить бота в чате
/on \\- включить бота обратно
/chance \\- установить вероятность ответов

📋 Используйте /help чтобы посмотреть все команды\\.

Просто напишите что\\-нибудь и посмотрите что получится\\! 😄"""

    await message.answer(welcome_text, parse_mode="MarkdownV2")
