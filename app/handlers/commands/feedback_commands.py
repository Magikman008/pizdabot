"""
Система обратной связи - полностью переписанная реализация
Обработчики команд для отправки и управления обращениями пользователей
ОБНОВЛЕНО: принимает любые текстовые сообщения, не только команды
"""
import asyncio
from datetime import datetime

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.controllers.admin_notifier import admin_notifier
from app.controllers.feedback_manager import feedback_manager
from app.states import FeedbackStates
from app.utils.decorators import admin_only
from app.utils.tools import escape_markdown

# Создаем роутер для системы обратной связи
feedback_router = Router(name="feedback_system")


async def notify_admins_about_new_feedback(
    feedback_id: int,
    user_display: str,
    message_preview: str,
    full_message: str
) -> int:
    """
    Legacy: рассылка уведомлений новым feedback.
    Использует notify_all для отправки всем зарегистрированным админам.
    """

    notification_text = (
        f"🔔 *Новое обращение №{feedback_id}*\n\n"
        f"👤 *От:* {user_display}\n"
        f"📅 *Время:* {str(datetime.now().strftime('%d.%m.%y %H:%M'))}\n\n"
        f"💬 *Сообщение:*\n{message_preview}\n\n"
        f"_Используйте `/feedback_detail {feedback_id}` для просмотра полного текста_"
    )

    # Асинхронная рассылка всем зарегистрированным админам
    success_count = await admin_notifier.notify_all(escape_markdown(notification_text))

    print(f"📊 Отправлено уведомлений: {success_count}")
    return success_count


@feedback_router.message(Command("feedback"))
async def cmd_feedback_start(message: Message, state: FSMContext):
    """
    Команда /feedback - начало процесса отправки обращения
    """
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"

    print(f"🎯 /feedback вызвана пользователем {user_id} (@{username})")

    # Устанавливаем состояние ожидания сообщения
    await state.set_state(FeedbackStates.waiting_for_message)

    # Текст инструкции в MarkdownV2
    instruction_text = (
        "📝 *Отправка обращения*\n\n"
        "Для отправки отзыва напишите его ниже\\. "
        "Изображения и видео прикрепляйте ссылкой, а не вложением \\-\\- "
        "иначе мы не сможем их просмотреть\\.\n\n"
        "*Напишите ваше сообщение \\(любой текст, не обязательно команду\\):*"
    )

    await message.answer(
        text=instruction_text,
        parse_mode="MarkdownV2"
    )

@feedback_router.message(FeedbackStates.waiting_for_message, F.text)
async def process_feedback_message(message: Message, state: FSMContext):
    """
    Обработка ЛЮБОГО текстового сообщения пользователя в состоянии ожидания
    Принимает как команды, так и обычный текст
    """
    user_id = message.from_user.id
    message_text = message.text

    print(f"📝 Получено сообщение от {user_id}: '{message_text[:50]}...' ({len(message_text)} символов)")

    # Проверяем, что это не команда отмены (для удобства пользователей)
    if message_text.lower() in ['/cancel', '/отмена', 'отмена', 'cancel']:
        await message.answer(
            "❌ *Отправка обращения отменена*\n\n"
            "Чтобы начать заново, используйте команду /feedback",
            parse_mode="MarkdownV2"
        )
        await state.clear()
        return

    # Валидация входящего сообщения
    if not message_text or len(message_text.strip()) < 5:
        await message.answer(
            "❌ *Сообщение слишком короткое*\n\n"
            "Напишите минимум 5 символов\\.\n"
            "_Или напишите 'отмена' для выхода_",
            parse_mode="MarkdownV2"
        )
        return

    if len(message_text) > 2000:
        await message.answer(
            "❌ *Сообщение слишком длинное*\n\n"
            "Максимум 2000 символов\\.\n"
            f"_Сейчас: {escape_markdown(str(len(message_text)))} символов_",
            parse_mode="MarkdownV2"
        )
        return

    # Сохраняем все данные в состояние FSM
    await state.update_data(
        feedback_message=message_text,
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
        message_timestamp=datetime.now().isoformat()
    )

    # Формируем отображаемое имя пользователя
    if message.from_user.username:
        user_display = f"@{message.from_user.username}"
    elif message.from_user.first_name:
        full_name = message.from_user.first_name
        if message.from_user.last_name:
            full_name += f" {message.from_user.last_name}"
        user_display = full_name
    else:
        user_display = f"User {user_id}"

    # Создаем превью сообщения с экранированием для MarkdownV2
    escaped_user = escape_markdown(user_display)
    escaped_message = escape_markdown(message_text)

    preview_text = (
        f"📋 *Предварительный просмотр вашего обращения:*\n\n"
        f"👤 *От:* {escaped_user}\n"
        f"📝 *Сообщение:*\n```\n{escaped_message}\n```\n\n"
        f"_Так это будет видно администраторам_\n\n"
        f"*Отправить обращение?*"
    )

    # Создаем inline клавиатуру для подтверждения
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="feedback_confirm"),
            InlineKeyboardButton(text="❌ Нет", callback_data="feedback_cancel")
        ]
    ])

    await message.answer(
        text=preview_text,
        parse_mode="MarkdownV2",
        reply_markup=confirm_keyboard
    )

    # Переводим в состояние подтверждения
    await state.set_state(FeedbackStates.confirming_send)

@feedback_router.message(FeedbackStates.waiting_for_message)
async def process_non_text_feedback_message(message: Message, state: FSMContext):
    """
    Обработка НЕ-текстовых сообщений в состоянии ожидания
    (фото, видео, стикеры и т.д.)
    """
    user_id = message.from_user.id
    print(f"📎 Получено НЕ-текстовое сообщение от {user_id}")

    message_type = ""
    if message.photo:
        message_type = "фото"
    elif message.video:
        message_type = "видео"
    elif message.document:
        message_type = "документ"
    elif message.sticker:
        message_type = "стикер"
    elif message.voice:
        message_type = "голосовое сообщение"
    elif message.video_note:
        message_type = "видео-сообщение"
    else:
        message_type = "медиа-контент"

    await message.answer(
        f"❌ *Неподдерживаемый тип сообщения*\n\n"
        f"Вы отправили: _{escape_markdown(message_type)}_\n\n"
        f"Пожалуйста, отправьте *обычный текст* для обращения\\.\n"
        f"Изображения и видео прикрепляйте как ссылки в тексте\\.\n\n"
        f"_Или напишите 'отмена' для выхода_",
        parse_mode="MarkdownV2"
    )

@feedback_router.callback_query(F.data == "feedback_confirm")
async def confirm_feedback_submission(callback: CallbackQuery, state: FSMContext):
    """
    Обработка подтверждения отправки обращения
    """
    user_data = await state.get_data()
    user_id = callback.from_user.id

    print(f"✅ Подтверждение обращения от {user_id}")

    # Сохраняем обращение в базу данных
    feedback_id = feedback_manager.add_feedback(
        user_id=user_data["user_id"],
        username=user_data.get("username"),
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        message=user_data["feedback_message"]
    )

    if feedback_id:
        # Успешное сохранение
        escaped_id = escape_markdown(str(feedback_id))
        success_text = (
            f"✅ *Обращение отправлено\\!*\n\n"
            f"📋 *ID обращения:* \\#{escaped_id}\n\n"
            f"Спасибо за обратную связь\\! "
            f"Администраторы рассмотрят ваше сообщение\\."
        )

        await callback.message.edit_text(
            text=success_text,
            parse_mode="MarkdownV2"
        )

        # Отправляем уведомления администраторам
        user_display = f"@{user_data.get('username')}" if user_data.get('username') else user_data.get('first_name', f"User {user_data['user_id']}")
        message_preview = user_data["feedback_message"]
        if len(message_preview) > 200:
            message_preview = message_preview[:200] + "..."

        # Асинхронно отправляем уведомления
        asyncio.create_task(
            notify_admins_about_new_feedback(
                feedback_id,
                user_display,
                message_preview,
                user_data["feedback_message"]
            )
        )

        print(f"🎉 УСПЕХ: Обращение #{feedback_id} от {user_id} сохранено и отправлены уведомления")

    else:
        # Ошибка сохранения
        error_text = (
            "❌ *Произошла ошибка при отправке обращения*\n\n"
            "Попробуйте позже или обратитесь к администраторам\\."
        )

        await callback.message.edit_text(
            text=error_text,
            parse_mode="MarkdownV2"
        )

        print(f"💥 ОШИБКА: Не удалось сохранить обращение от {user_id}")

    # Очищаем состояние FSM
    await state.clear()
    await callback.answer()

@feedback_router.callback_query(F.data == "feedback_cancel")
async def cancel_feedback_submission(callback: CallbackQuery, state: FSMContext):
    """
    Обработка отмены отправки обращения
    """
    user_id = callback.from_user.id
    print(f"❌ Отмена обращения от {user_id}")

    cancel_text = (
        "❌ *Отправка обращения отменена*\n\n"
        "Чтобы начать заново, используйте команду /feedback"
    )

    await callback.message.edit_text(
        text=cancel_text,
        parse_mode="MarkdownV2"
    )

    await state.clear()
    await callback.answer()


@feedback_router.message(Command("feedback_detail"))
@admin_only
async def cmd_feedback_detail(message: Message):
    """
    Просмотр детального обращения по ID
    """
    username = message.from_user.username

    # Автоматически регистрируем админа
    await admin_notifier.register_admin(username, message.chat.id)

    try:
        # Извлекаем ID из команды
        args = message.text.split()
        if len(args) < 2:
            await message.answer(
                "❌ *Укажите ID обращения*\n\n"
                "_Пример:_ /feedback\\_detail 1",
                parse_mode="MarkdownV2"
            )
            return

        feedback_id = int(args[1])
        feedback_data = feedback_manager.get_feedback_by_id(feedback_id)

        if not feedback_data:
            escaped_id = escape_markdown(str(feedback_id))
            await message.answer(
                f"❌ *Обращение \\#{escaped_id} не найдено*",
                parse_mode="MarkdownV2"
            )
            return

        # Отмечаем как прочитанное
        feedback_manager.mark_as_read(feedback_id)

        # Формируем детальную информацию
        user_display = feedback_data.get('username', feedback_data.get('first_name', f"User {feedback_data['user_id']}"))
        if feedback_data.get('username'):
            user_display = f"@{user_display}"

        status_text = "Прочитано" if feedback_data['is_read'] else "Новое"
        created_at = feedback_data['created_at'][:16].replace('T', ' ')

        # Экранируем для MarkdownV2
        escaped_id = escape_markdown(str(feedback_data['id']))
        escaped_user = escape_markdown(user_display)
        escaped_date = escape_markdown(created_at)
        escaped_status = escape_markdown(status_text)
        escaped_message = escape_markdown(feedback_data['message'])

        detail_text = (
            f"📋 *Обращение \\#{escaped_id}*\n\n"
            f"👤 *От:* {escaped_user}\n"
            f"📅 *Дата:* {escaped_date}\n"
            f"👁️ *Статус:* {escaped_status}\n\n"
            f"📝 *Сообщение:*\n```\n{escaped_message}\n```"
        )

        await message.answer(
            text=detail_text,
            parse_mode="MarkdownV2"
        )

        print(f"👁️ Обращение #{feedback_id} просмотрено админом @{username}")

    except ValueError:
        await message.answer(
            "❌ *Неверный формат ID*\n\nУкажите число\\.",
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        escaped_error = escape_markdown(str(e))
        await message.answer(
            f"❌ *Ошибка при получении обращения:*\n{escaped_error}",
            parse_mode="MarkdownV2"
        )

@feedback_router.message(Command("feedback_stats"))
@admin_only
async def cmd_feedback_stats(message: Message):
    """
    Статистика по обращениям
    """
    username = message.from_user.username

    # Автоматически регистрируем админа
    await admin_notifier.register_admin(username, message.chat.id)

    # Получаем статистику
    stats = feedback_manager.get_stats()

    # Экранируем числовые значения
    escaped_total = escape_markdown(str(stats['total_count']))
    escaped_unread = escape_markdown(str(stats['unread_count']))
    escaped_read = escape_markdown(str(stats['read_count']))
    escaped_users = escape_markdown(str(stats['unique_users']))

    stats_text = (
        f"📊 *Статистика обращений*\n\n"
        f"📝 *Всего обращений:* {escaped_total}\n"
        f"🔴 *Непрочитанных:* {escaped_unread}\n"
        f"✅ *Прочитанных:* {escaped_read}\n"
        f"👥 *Уникальных пользователей:* {escaped_users}\n"
    )

    if stats['last_feedback_date']:
        last_date = stats['last_feedback_date'][:16].replace('T', ' ')
        escaped_date = escape_markdown(last_date)
        stats_text += f"🕐 *Последнее обращение:* {escaped_date}"
    else:
        stats_text += "🕐 *Обращений пока нет*"

    await message.answer(
        text=stats_text,
        parse_mode="MarkdownV2"
    )