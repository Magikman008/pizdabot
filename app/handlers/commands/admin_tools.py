from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers import bot_stats, subscription_manager
from app.controllers.admin_notifier import admin_notifier
from app.controllers.feedback_manager import feedback_manager
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

@admin_router.message(Command("admin_register"))
@admin_only
async def cmd_admin_register(message: Message):

    # Регистрируем администратора
    admin_notifier.register_admin(message.from_user.username, message.chat.id)

    await message.answer(
        f"✅ **Вы зарегистрированы как администратор!**\n\n"
        f"👤 Username: @{message.from_user.username}\n"
        f"🆔 Chat ID: {message.chat.id}\n\n"
        f"Теперь вы будете получать уведомления о новых обращениях.",
        parse_mode="markdownV2"
    )


@admin_router.message(Command("feedback_mark_all_read"))
@admin_only
async def cmd_mark_all_read(message: Message):
    count = feedback_manager.mark_all_as_read()

    if count > 0:
        await message.answer(
            f"✅ **Отмечено как прочитанные: {count} обращений**",
            parse_mode="markdownV2"
        )
    else:
        await message.answer("ℹ️ Нет непрочитанных обращений.")


@admin_router.message(Command("feedback_unread"))
@admin_only
async def cmd_feedback_unread(message: Message):
    feedbacks = feedback_manager.get_all_feedback(limit=10, unread_only=True)

    if not feedbacks:
        await message.answer(
            "✅ **Нет непрочитанных обращений**\n\n"
            "Все обращения обработаны!",
            parse_mode="markdownV2"
        )
        return

    response_text = f"🔴 **Непрочитанные обращения ({len(feedbacks)}):**\n\n"

    for feedback in feedbacks:
        user_display = feedback.get('username', feedback.get('first_name',
                                                             f"User {feedback['user_id']}"))
        if feedback.get('username'):
            user_display = f"@{user_display}"

        # Обрезаем длинные сообщения
        message_preview = feedback['message']
        if len(message_preview) > 150:
            message_preview = message_preview[:150] + "..."

        created_at = feedback['created_at'][:16].replace('T', ' ')

        response_text += (
            f"🆔 **#{feedback['id']}** | {user_display}\n"
            f"📅 {created_at}\n"
            f"💬 {message_preview}\n\n"
        )

    response_text += "*Используйте /feedback_detail [ID] для просмотра*"

    await message.answer(escape_markdown(response_text), parse_mode="markdownV2")


@admin_router.message(Command("feedback_delete"))
@admin_only
async def cmd_feedback_delete(message: Message):
    try:
        # Извлекаем ID из команды
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите ID обращения. Пример: /feedback_delete 1")
            return

        feedback_id = int(args[1])

        # Проверяем, существует ли обращение
        feedback_data = feedback_manager.get_feedback_by_id(feedback_id)
        if not feedback_data:
            await message.answer(f"❌ Обращение #{feedback_id} не найдено.")
            return

        # Удаляем обращение
        success = feedback_manager.delete_feedback(feedback_id)

        if success:
            await message.answer(
                f"✅ **Обращение #{feedback_id} удалено**",
                parse_mode="markdownV2"
            )
        else:
            await message.answer(f"❌ Ошибка при удалении обращения #{feedback_id}.")

    except ValueError:
        await message.answer("❌ Неверный формат ID. Укажите число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении обращения: {e}")


@admin_router.message(Command("feedback_user"))
@admin_only
async def cmd_feedback_user(message: Message):
    try:
        # Извлекаем user_id из команды
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите user_id. Пример: /feedback_user 123456789")
            return

        user_id = int(args[1])
        feedbacks = feedback_manager.get_feedback_by_user(user_id, limit=10)

        if not feedbacks:
            await message.answer(
                f"📭 **Обращений от пользователя {user_id} не найдено**")
            return

        # Берем информацию о пользователе из первого обращения
        first_feedback = feedbacks[0]
        user_display = first_feedback.get('username', first_feedback.get('first_name',
                                                                         f"User {user_id}"))
        if first_feedback.get('username'):
            user_display = f"@{user_display}"

        response_text = (
            f"👤 **Обращения пользователя {user_display}**\n"
            f"📊 Всего: {len(feedbacks)}\n\n"
        )

        for feedback in feedbacks:
            status = "🔴" if not feedback['is_read'] else "✅"
            message_preview = feedback['message']
            if len(message_preview) > 100:
                message_preview = message_preview[:100] + "..."

            created_at = feedback['created_at'][:16].replace('T', ' ')

            response_text += (
                f"{status} **#{feedback['id']}** | {created_at}\n"
                f"💬 {message_preview}\n\n"
            )

        await message.answer(escape_markdown(response_text), parse_mode="markdownV2")

    except ValueError:
        await message.answer("❌ Неверный формат user_id. Укажите число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении обращений: {e}")


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
    await message.answer(escape_markdown(help_text), parse_mode="markdownV2")
