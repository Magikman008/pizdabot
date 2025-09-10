"""
Административные команды для системы обратной связи
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers.feedback_manager import feedback_manager
from app.controllers.admin_notifier import admin_notifier
from settings import ADMIN_USERNAMES

# Создаем роутер для админских команд
admin_commands_router = Router()


def is_admin(username: str) -> bool:
    """Проверить, является ли пользователь администратором"""
    return username and username in ADMIN_USERNAMES


@admin_commands_router.message(Command("admin_register"))
async def cmd_admin_register(message: Message):
    """Зарегистрировать администратора для получения уведомлений"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    # Регистрируем администратора
    admin_notifier.register_admin(message.from_user.username, message.chat.id)

    await message.answer(
        f"✅ **Вы зарегистрированы как администратор!**\n\n"
        f"👤 Username: @{message.from_user.username}\n"
        f"🆔 Chat ID: {message.chat.id}\n\n"
        f"Теперь вы будете получать уведомления о новых обращениях.",
        parse_mode="HTML"
    )


@admin_commands_router.message(Command("feedback_mark_all_read"))
async def cmd_mark_all_read(message: Message):
    """Отметить все обращения как прочитанные"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    count = feedback_manager.mark_all_as_read()

    if count > 0:
        await message.answer(
            f"✅ **Отмечено как прочитанные: {count} обращений**",
            parse_mode="HTML"
        )
    else:
        await message.answer("ℹ️ Нет непрочитанных обращений.")


@admin_commands_router.message(Command("feedback_unread"))
async def cmd_feedback_unread(message: Message):
    """Показать только непрочитанные обращения"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    feedbacks = feedback_manager.get_all_feedback(limit=10, unread_only=True)

    if not feedbacks:
        await message.answer(
            "✅ **Нет непрочитанных обращений**\n\n"
            "Все обращения обработаны!",
            parse_mode="HTML"
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

    await message.answer(response_text, parse_mode="HTML")


@admin_commands_router.message(Command("feedback_delete"))
async def cmd_feedback_delete(message: Message):
    """Удалить обращение по ID"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

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
                parse_mode="HTML"
            )
        else:
            await message.answer(f"❌ Ошибка при удалении обращения #{feedback_id}.")

    except ValueError:
        await message.answer("❌ Неверный формат ID. Укажите число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при удалении обращения: {e}")


@admin_commands_router.message(Command("feedback_user"))
async def cmd_feedback_user(message: Message):
    """Показать все обращения конкретного пользователя"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

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

        await message.answer(response_text, parse_mode="HTML")

    except ValueError:
        await message.answer("❌ Неверный формат user_id. Укажите число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении обращений: {e}")


@admin_commands_router.message(Command("admin_help"))
async def cmd_admin_help(message: Message):
    """Справка по административным командам"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    help_text = (
        "🛠 **Административные команды системы обратной связи:**\n\n"

        "**📋 Просмотр обращений:**\n"
        "• `/admin_feedback` - все обращения\n"
        "• `/feedback_unread` - только непрочитанные\n"
        "• `/feedback_detail [ID]` - детали обращения\n"
        "• `/feedback_user [user_id]` - обращения пользователя\n"
        "• `/feedback_stats` - статистика обращений\n\n"

        "**⚙️ Управление:**\n"
        "• `/admin_register` - регистрация для уведомлений\n"
        "• `/feedback_mark_all_read` - отметить все как прочитанные\n"
        "• `/feedback_delete [ID]` - удалить обращение\n\n"

        "**📊 Дополнительно:**\n"
        "• `/admin_help` - эта справка\n\n"

        "*Для получения уведомлений о новых обращениях обязательно выполните `/admin_register`*"
    )

    await message.answer(help_text, parse_mode="HTML")