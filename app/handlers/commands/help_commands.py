"""
Полное обновленное руководство /help для бота PizdaBot
Включает ВСЕ команды из всех модулей системы
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from app.utils.tools import is_admin, has_premium_access, escape_markdown

# Создаем роутер для команд помощи
help_router = Router()

@help_router.message(Command("help"))
async def cmd_help(message: Message):
    """
    Команда /help - полный список всех доступных команд
    """
    user_id = message.from_user.id
    user_is_admin = is_admin(message)
    user_has_premium = has_premium_access(user_id)

    # Заголовок
    help_text = (
        "🤖 *Команды бота Подъёбыш*\n\n"
    )

    # === СИСТЕМА ОБРАТНОЙ СВЯЗИ ===
    help_text += (
        "📝 *Система обратной связи:*\n"
        "• /feedback — отправить обращение администраторам\n"
        "  _После команды просто напишите любой текст (не команду)_\n\n"
    )

    # === УПРАВЛЕНИЕ БОТОМ ===
    help_text += (
        "⚙️ *Управление ботом:*\n"
        "• /on — включить бота в чате\n"
        "• /off — выключить бота в чате\n"
        "• /chance <0–100> — установить вероятность ответа (%)\n"
        "• /settings — показать текущие настройки чата\n\n"
    )

    # === ПРЕМИУМ И ПОДПИСКИ ===
    help_text += (
        "⭐ *Подписка и премиум:*\n"
        "• /sub — купить премиум-подписку за 1 звёздочку\n"
    )
    if user_has_premium:
        help_text += "• ✅ *Премиум-статус активен!*\
\n"
    else:
        help_text += "• ❌ _Премиум-статус неактивен_\n"
    help_text += "\n"

    # === ПОЛЬЗОВАТЕЛЬСКИЕ ТРИГГЕРЫ ===
    help_text += (
        "🎯 *Пользовательские триггеры* "
    )
    if user_has_premium:
        help_text += "(доступно):\n"
        help_text += (
            '• /add "фраза" "ответ" — добавить триггер (безлимитно)\n'
            '• /remove "фраза" — удалить свой триггер\n'
            "• /triggers — список триггеров чата\n\n"
        )
    else:
        help_text += "(только для подписчиков):\n"
        help_text += (
            '• /add "фраза" "ответ" — добавить триггер 🔒\n'
            '• /remove "фраза" — удалить триггер 🔒\n'
            "• /triggers — список триггеров чата\n"
            "_Для доступа купите подписку через_ /sub\n\n"
        )

    # === СТАТИСТИКА ===
    help_text += (
        "📊 *Статистика:*\n"
        "• /stats — общая статистика бота\n"
        "• /top — топ-10 популярных триггеров\n\n"
    )

    # === ИНФОРМАЦИЯ ===
    help_text += (
        "ℹ️ *Информация:*\n"
        "• /help — показать это сообщение\n"
        "• /start — приветствие бота\n\n"
    )

    # === АДМИНИСТРАТИВНЫЕ КОМАНДЫ ===
    if user_is_admin:
        help_text += (
            "👑 *Административные команды:*\n\n"
            "*Обратная связь:*\n"
            "• /admin_register — регистрация для уведомлений о новых обращениях\n"
            "• /admin_feedback — просмотр всех обращений\n"
            "• /feedback_detail [ID] — детальный просмотр обращения\n"
            "• /feedback_stats — статистика по обращениям\n\n"
            "*Общее управление:*\n"
            "• /admin_stats — детальная статистика бота\n"
            "• /reset_settings — сбросить настройки чата\n"
            "• /subscribers — список активных подписчиков\n\n"
            "*Примеры использования:*\n"
            "/admin_register\n"
            "/feedback_detail 5\n"
            "/chance 75\n\n"
        )

    # === ДОПОЛНИТЕЛЬНАЯ ИНФОРМАЦИЯ ===
    help_text += (
        "💡 *Как работает система обратной связи:*\n"
        "1. Напишите /feedback\n"
        "2. Отправьте любое текстовое сообщение\n"
        "3. Подтвердите отправку кнопкой\n"
        "4. Получите ID обращения для отслеживания\n\n"
        "⚠️ *Важные моменты:*\n"
        "• Изображения и видео прикрепляйте как ссылки в тексте\n"
        "• Минимум 5 символов, максимум 2000\n"
        "• Для отмены процесса напишите 'отмена'\n"
    )

    # === ОСОБЫЕ УКАЗАНИЯ ===
    if user_is_admin:
        help_text += (
            "\n🔔 *Для администраторов:*\n"
            "_Обязательно выполните_ /admin_register _для получения уведомлений о новых обращениях!_"
        )
    elif not user_has_premium:
        help_text += (
            "\n⭐ *Хотите больше возможностей?*\n"
            "Приобретите премиум-подписку через /sub всего за 1 звёздочку!"
        )
    else:
        help_text += (
            "\n✨ *Спасибо за поддержку проекта!*\n"
            "У вас активен премиум-доступ ко всем функциям."
        )

    await message.answer(
        text=escape_markdown(help_text),
        parse_mode="MarkdownV2"
    )

@help_router.message(Command("start"))
async def cmd_start(message: Message):
    """
    Команда /start - расширенное приветствие пользователя
    """
    username = message.from_user.username or message.from_user.first_name or "пользователь"
    user_id = message.from_user.id
    user_is_admin = is_admin(message.from_user.username)
    user_has_premium = has_premium_access(user_id)
    escaped_username = escape_markdown(username)

    # Основное приветствие
    start_text = (
        f"👋 *Добро пожаловать, {escaped_username}!*\n\n"
        "🤖 Я бот *Подъёбыш* — отвечаю на различные фразы забавными ответами.\n\n"
    )

    # Информация о статусе пользователя
    if user_is_admin:
        start_text += (
            "👑 *Вы — администратор!*\n"
            "Доступны все функции управления ботом.\n"
            "Не забудьте выполнить /admin_register для уведомлений.\n\n"
        )
    elif user_has_premium:
        start_text += (
            "⭐ *У вас активна премиум-подписка!*\n"
            "Доступны все функции, включая пользовательские триггеры.\n\n"
        )
    else:
        start_text += (
            "🎯 *Базовый доступ*\n"
            "Для расширенных возможностей приобретите премиум через /sub.\n\n"
        )

    # Основные возможности
    start_text += (
        "📝 *Главная функция — система обратной связи:*\n"
        "• Используйте /feedback для отправки обращений администраторам\n"
        "• Просто напишите команду, затем любое текстовое сообщение\n\n"
        "⚙️ *Управление ботом в чате:*\n"
        "• /off — выключить бота\n"
        "• /on — включить бота\n"
        "• /chance <число> — настроить вероятность ответов\n\n"
    )

    if not user_has_premium and not user_is_admin:
        start_text += (
            "⭐ *Премиум-возможности (за 1 звёздочку):*\n"
            "• Добавление пользовательских триггеров\n"
            "• Безлимитное количество триггеров\n"
            "• Эксклюзивные функции\n"
            "• Приоритетная обработка\n\n"
            "💫 Команда /sub для покупки подписки!\n\n"
        )

    start_text += (
        "ℹ️ *Для полного списка команд используйте* /help\n\n"
        "🎭 *Попробуйте написать что-нибудь и посмотрите, что получится!* 😄"
    )

    await message.answer(
        text=escape_markdown(start_text),
        parse_mode="MarkdownV2"
    )

@help_router.message(Command("commands"))
async def cmd_commands(message: Message):
    """
    Команда /commands - краткий список команд (алиас для /help)
    """
    await cmd_help(message)
