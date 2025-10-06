import logging
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers import admin_notifier, chat_info_manager
from app.controllers import bot_stats, subscription_manager
from app.controllers import feedback_manager
from app.models.chat_info import ChatInfo
from app.utils.decorators import admin_only
from app.utils.tools import escape_markdown, is_admin, split_long_message

admin_router = Router()


@admin_router.message(Command("admin_stats"))
@admin_only
async def admin_stats(message: Message):
    """Детальная статистика (только для админов)"""
    detailed_stats = bot_stats.get_admin_stats()

    # Добавляем информацию о подписчиках
    subscribers = subscription_manager.get_all_subscribers()
    detailed_stats += f"\n\n⭐ Активных подписчиков: {len(subscribers)}"

    text = detailed_stats
    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("subscribers"))
@admin_only
async def show_subscribers(message: Message):
    """Показать список подписчиков (только для админов)"""
    subscribers = subscription_manager.get_all_subscribers()

    if not subscribers:
        text = "📋 Активных подписчиков нет"
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
        return

    text = f"👥 *Активные подписчики ({len(subscribers)}):*\n\n"

    for i, (tg_chat_id, sub) in enumerate(subscribers.items(), 1):
        expires_at = sub.expires_at
        if isinstance(expires_at, datetime):
            expires_at_str = expires_at.strftime("%d.%m.%y %H:%M")
        else:
            expires_at_str = str(expires_at)[:16]  # на всякий случай

        text += f"{i}. ID: {tg_chat_id} (до {expires_at_str})\n"

    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("admin_register"))
@admin_only
async def cmd_admin_register(message: Message):
    # Регистрируем администратора
    admin_notifier.register_admin(message.from_user.username, message.chat.id)

    text = (
        "✅ **Вы зарегистрированы как администратор!**\n\n"
        f"👤 Username: @{message.from_user.username}\n"
        f"🆔 Chat ID: {message.chat.id}\n\n"
        "Теперь вы будете получать уведомления о новых обращениях."
    )
    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("feedback_mark_all_read"))
@admin_only
async def cmd_mark_all_read(message: Message):
    count = feedback_manager.mark_all_as_read()

    if count > 0:
        text = f"✅ **Отмечено как прочитанные: {count} обращений**"
    else:
        text = "ℹ️ Нет непрочитанных обращений."

    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("feedback_unread"))
@admin_only
async def cmd_feedback_unread(message: Message):
    feedbacks = feedback_manager.get_all_feedback(limit=100, unread_only=True)

    if not feedbacks:
        text = "✅ **Нет непрочитанных обращений**\n\n" "Все обращения обработаны!"
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
        return

    text = f"🔴 **Непрочитанные обращения ({len(feedbacks)}):**\n\n"

    for fb in feedbacks:
        user_display = fb.username or fb.first_name or f"User {fb.user_id}"
        if fb.get("username"):
            user_display = f"@{user_display}"

        message_preview = fb["message"]
        if len(message_preview) > 150:
            message_preview = message_preview[:150] + "..."

        created_at = fb["created_at"][:16].replace("T", " ")

        text += (
            f"🆔 **#{fb['id']}** | {user_display}\n"
            f"📅 {created_at}\n"
            f"💬 {message_preview}\n\n"
        )

    text += "*Используйте /feedback_detail [ID] для просмотра*"
    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("feedback_delete"))
@admin_only
async def cmd_feedback_delete(message: Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            text = "❌ Укажите ID обращения. Пример: /feedback_delete 1"
            await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
            return

        feedback_id = int(args[1])
        feedback = feedback_manager.get_feedback_by_id(feedback_id)
        if not feedback:
            text = f"❌ Обращение #{feedback_id} не найдено."
            await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
            return

        success = feedback_manager.delete_feedback(feedback_id)
        if success:
            text = f"✅ **Обращение #{feedback_id} удалено**"
        else:
            text = f"❌ Ошибка при удалении обращения #{feedback_id}."
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")

    except ValueError:
        text = "❌ Неверный формат ID. Укажите число."
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
    except Exception as e:
        text = f"❌ Ошибка при удалении обращения: {e}"
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("feedback_user"))
@admin_only
async def cmd_feedback_user(message: Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            text = "❌ Укажите user_id. Пример: /feedback_user 123456789"
            await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
            return

        user_id = int(args[1])
        feedbacks = feedback_manager.get_feedback_by_user(user_id, limit=100)
        if not feedbacks:
            text = f"📭 **Обращений от пользователя {user_id} не найдено**"
            await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
            return

        first = feedbacks[0]
        user_display = first.get("username", first.get("first_name", f"User {user_id}"))
        if first.get("username"):
            user_display = f"@{user_display}"

        text = (
            f"👤 **Обращения пользователя {user_display}**\n"
            f"📊 Всего: {len(feedbacks)}\n\n"
        )

        for fb in feedbacks:
            status = "🔴" if not fb["is_read"] else "✅"
            message_preview = fb["message"]
            if len(message_preview) > 100:
                message_preview = message_preview[:100] + "..."
            created_at = fb["created_at"][:16].replace("T", " ")
            text += (
                f"{status} **#{fb['id']}** | {created_at}\n" f"💬 {message_preview}\n\n"
            )

        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")

    except ValueError:
        text = "❌ Неверный формат user_id. Укажите число."
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
    except Exception as e:
        text = f"❌ Ошибка при получении обращений: {e}"
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("admin_feedback"))
@admin_only
async def cmd_admin_feedback(message: Message):
    """
    Просмотр всех обращений (только для администраторов)
    """
    if not is_admin(message):
        text = "❌ *Эта команда доступна только администраторам*"
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
        return

    feedbacks = feedback_manager.get_all_feedback(limit=100)
    unread_count = feedback_manager.get_unread_count()

    if not feedbacks:
        text = (
            "📭 *Обращений пока нет*\n\n"
            "Пользователи еще не отправляли обратную связь\\."
        )
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
        return

    total = escape_markdown(str(len(feedbacks)))
    unread = escape_markdown(str(unread_count))

    text = (
        f"📬 *Обращения пользователей*\n\n"
        f"📊 *Всего:* {total} | 🔔 *Непрочитанных:* {unread}\n\n"
    )

    for fb in feedbacks[:10]:
        status = "🔴" if not fb.is_read else "✅"
        user_display = fb.username or fb.first_name or f"User {fb.user_id}"
        if fb.username:
            user_display = f"@{user_display}"
        message_preview = fb.message
        if len(message_preview) > 100:
            message_preview = message_preview[:100] + "..."
        created_at = fb.created_at.isoformat()[:16].replace("T", " ")
        text += (
            f"{status} *#{escape_markdown(str(fb.id))}* | {user_display}\n"
            f"📅 {created_at}\n"
            f"💬 {escape_markdown(message_preview)}\n"
            f"👀 `/feedback_detail {str(fb.id)}` \n\n"
        )

    text += "Используйте /feedback_detail [ID] для просмотра полного текста"
    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("admin_help"))
@admin_only
async def cmd_admin_help(message: Message):
    help_text = """🔧 **Административные команды:**

📊 **Статистика:**
• `/admin_stats` - детальная статистика бота
• `/export_stats` - экспорт статистики в JSON

🗑 **Управление данными:**  
• `/clear_stats` - очистить всю статистику
• `/remove_all_triggers` - удалить все триггеры чата
• `/reset_settings` - сбросить настройки чата

💬 **Управление чатами:**
• `/update_chats` - обновить информацию о всех чатах
• `/show_chats` - показать список всех чатов

📝 **Система обратной связи:**
• `/admin_register` - регистрация для уведомлений
• `/admin_feedback` - просмотр всех обращений
• `/feedback_unread` - непрочитанные обращения
• `/feedback_stats` - статистика по обращениям
• `/feedback_mark_all_read` - отметить все как прочитанные

ℹ️ **Справка:**
• `/admin_help` - эта справка"""

    await message.answer(escape_markdown(help_text), parse_mode="MarkdownV2")


@admin_router.message(Command("update_chats"))
@admin_only
async def update_all_chats_command(message: Message):
    """Команда для обновления информации о всех чатах"""
    start_time = datetime.now()
    status_msg = await message.reply(
        "🔄 Обновление информации о чатах\n\n"
        "⏳ Получаем список активных чатов и начинаем обновление..."
    )

    try:
        stats = await chat_info_manager.update_all_chats_info()
        end_time = datetime.now()
        execution_time = (end_time - start_time).total_seconds()

        report = f"""✅ **Обновление чатов завершено**

📊 **Статистика обновления:**
• Всего чатов обработано: **{stats['total']}**
• Успешно обновлено: **{stats['updated']}** ✅
• Деактивировано (бот удален): **{stats['deactivated']}** ⚠️
• Ошибок при обновлении: **{stats['errors']}** ❌

⏱ **Время выполнения:** {execution_time:.1f} сек
📅 **Завершено:** {end_time.strftime('%H:%M:%S %d.%m.%Y')}"""

        if stats['errors'] > 0:
            report += "\n\n⚠️ *Подробности ошибок смотрите в логах бота*"

        if stats['deactivated'] > 0:
            report += f"\n\n📝 *{stats['deactivated']} чатов помечено как неактивных (бот удален)*"

        await status_msg.edit_text(report, parse_mode="Markdown")

    except Exception as e:
        error_msg = f"❌ **Ошибка при обновлении чатов**\n\n🔍 Детали: `{str(e)}`"
        await status_msg.edit_text(error_msg, parse_mode="Markdown")


@admin_router.message(Command("show_chats"))
@admin_only
async def show_chats_command(message: Message):
    """Команда для просмотра всех чатов"""

    try:
        chats_info = await get_all_chats_info()

        if not chats_info:
            await message.reply("📭 Чатов не найдено")
            return

        # Формируем сообщение с информацией о чатах
        response = "📋 **Все чаты бота:**\n\n"

        for i, chat in enumerate(chats_info, 1):
            # Форматируем дату добавления
            added_date = chat.added_at.strftime(
                "%d.%m.%Y %H:%M") if chat.added_at else "—"

            # Определяем статус бота
            status_emoji = "✅" if chat.is_active else "❌"
            status_text = "активен" if chat.is_active else "неактивен"

            # Форматируем тип чата
            chat_type_map = {
                'private': '👤 Личный',
                'group': '👥 Группа',
                'supergroup': '👥 Супергруппа',
                'channel': '📢 Канал'
            }
            chat_type_str = chat_type_map.get(chat.chat_type, chat.chat_type)

            # Обрезаем длинные названия и описания
            title = chat.chat_title[:30] + "..." if len(
                chat.chat_title) > 30 else chat.chat_title
            description = (chat.chat_description[
                           :50] + "...") if chat.chat_description and len(
                chat.chat_description) > 50 else (chat.chat_description or "—")

            response += f"""**{i}. {title}**
{chat_type_str} | {chat.members_count or "—"} чел.
📅 Добавлен: {added_date}
👤 Кем: @{chat.added_by_username or "неизвестно"}
📝 Описание: {description}
🤖 Бот: {status_emoji} {status_text}

"""

        # Telegram ограничивает размер сообщения, разбиваем если нужно
        if len(response) > 4000:
            messages = split_long_message(response, 4000)
            for msg in messages:
                await message.reply(msg, parse_mode="Markdown")
        else:
            await message.reply(response, parse_mode="Markdown")

    except Exception as e:
        await message.reply(f"❌ Ошибка при получении списка чатов: {str(e)}")
        logging.error(f"Ошибка команды show_chats: {e}")


async def get_all_chats_info():
    """Получить информацию о всех чатах, отсортированную по дате добавления"""

    try:
        with chat_info_manager.session_maker() as session:
            chats = session.query(ChatInfo).order_by(ChatInfo.added_at.desc()).all()
            return chats
    except Exception as e:
        logging.error(f"Ошибка получения списка чатов: {e}")
        return []
