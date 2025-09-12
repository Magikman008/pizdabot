from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers import bot_stats, subscription_manager
from app.controllers.admin_notifier import admin_notifier
from app.controllers.feedback_manager import feedback_manager
from app.utils.decorators import admin_only
from app.utils.tools import escape_markdown, is_admin

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
            expires_at_str = expires_at.strftime("%Y-%m-%d %H:%M")
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
    feedbacks = feedback_manager.get_all_feedback(limit=10, unread_only=True)

    if not feedbacks:
        text = (
            "✅ **Нет непрочитанных обращений**\n\n"
            "Все обращения обработаны!"
        )
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
        return

    text = f"🔴 **Непрочитанные обращения ({len(feedbacks)}):**\n\n"

    for fb in feedbacks:
        user_display = fb.get('username', fb.get('first_name', f"User {fb['user_id']}"))
        if fb.get('username'):
            user_display = f"@{user_display}"

        message_preview = fb['message']
        if len(message_preview) > 150:
            message_preview = message_preview[:150] + "..."

        created_at = fb['created_at'][:16].replace('T', ' ')

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
        feedback_data = feedback_manager.get_feedback_by_id(feedback_id)
        if not feedback_data:
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
        feedbacks = feedback_manager.get_feedback_by_user(user_id, limit=10)
        if not feedbacks:
            text = f"📭 **Обращений от пользователя {user_id} не найдено**"
            await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
            return

        first = feedbacks[0]
        user_display = first.get('username', first.get('first_name', f"User {user_id}"))
        if first.get('username'):
            user_display = f"@{user_display}"

        text = (
            f"👤 **Обращения пользователя {user_display}**\n"
            f"📊 Всего: {len(feedbacks)}\n\n"
        )

        for fb in feedbacks:
            status = "🔴" if not fb['is_read'] else "✅"
            message_preview = fb['message']
            if len(message_preview) > 100:
                message_preview = message_preview[:100] + "..."
            created_at = fb['created_at'][:16].replace('T', ' ')
            text += (
                f"{status} **#{fb['id']}** | {created_at}\n"
                f"💬 {message_preview}\n\n"
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
    username = message.from_user.username

    if not is_admin(message):
        text = "❌ *Эта команда доступна только администраторам*"
        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
        return

    await admin_notifier.register_admin(username, message.chat.id)

    feedbacks = feedback_manager.get_all_feedback(limit=10)
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
        status = "🔴" if not fb['is_read'] else "✅"
        user_display = fb.get('username', fb.get('first_name', f"User {fb['user_id']}"))
        if fb.get('username'):
            user_display = f"@{user_display}"
        message_preview = fb['message']
        if len(message_preview) > 100:
            message_preview = message_preview[:100] + "..."
        created_at = fb['created_at'][:16].replace('T', ' ')
        text += (
            f"{status} *#{escape_markdown(str(fb['id']))}* | {user_display}\n"
            f"📅 {created_at}\n"
            f"💬 {message_preview}\n\n"
        )

    text += "Используйте /feedback_detail [ID] для просмотра полного текста"
    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("admin_help"))
@admin_only
async def cmd_admin_help(message: Message):
    help_text = (
        "👑 *Административные команды:*\n\n"
        "*Обратная связь:*\n"
        "• /admin_register — регистрация для уведомлений о новых обращениях. "
        "*Обязательно выполните* для получения уведомлений о новых обращениях!\n"
        "• /admin_feedback — просмотр всех обращений\n"
        "• /feedback_unread — только непрочитанные\n"
        "• /feedback_detail [ID] — детальный просмотр обращения\n"
        "• /feedback_user [user_id] — обращения пользователя\n"
        "• /feedback_stats — статистика по обращениям\n\n"
        "*Общее управление:*\n"
        "• /admin_stats — детальная статистика бота\n"
        "• /reset_settings — сбросить настройки чата\n"
        "• /subscribers — список активных подписчиков\n"
        "• /feedback_mark_all_read — отметить все как прочитанные\n"
        "• /feedback_delete [ID] — удалить обращение\n\n"
        "📊 *Дополнительно:*\n"
        "• /admin_help — эта справка\n\n"
    )
    text = help_text
    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
