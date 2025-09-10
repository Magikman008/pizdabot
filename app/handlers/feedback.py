"""
Обработчики команд для системы обратной связи
"""
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram import F

from app.controllers.feedback_manager import feedback_manager
from app.states import FeedbackStates
from settings import ADMIN_USERNAMES

# Создаем роутер для feedback команд
feedback_router = Router()

def is_admin(username: str) -> bool:
    """Проверить, является ли пользователь администратором"""
    return username and username in ADMIN_USERNAMES

@feedback_router.message(Command("feedback"))
async def cmd_feedback(message: Message, state: FSMContext):
    """Начать процесс отправки обратной связи"""
    print(f"DEBUG: Команда /feedback получена от пользователя {message.from_user.id}")

    await state.set_state(FeedbackStates.waiting_for_message)
    await message.answer(
        "📝 <b>Отправка обратной связи</b>\n\n"
        "Для отправки отзыва напишите его ниже. "
        "Изображения и видео прикрепляйте ссылкой, а не вложением -- "
        "иначе мы не сможем их просмотреть.\n\n"
        "Напишите ваше сообщение:",
        parse_mode="HTML"
    )

@feedback_router.message(FeedbackStates.waiting_for_message)
async def process_feedback_message(message: Message, state: FSMContext):
    """Обработка сообщения обратной связи"""
    print(f"DEBUG: Получено сообщение в состоянии waiting_for_message: {message.text}")

    if not message.text or len(message.text.strip()) < 5:
        await message.answer(
            "❌ Сообщение слишком короткое. Напишите минимум 5 символов."
        )
        return

    if len(message.text) > 2000:
        await message.answer(
            "❌ Сообщение слишком длинное. Максимум 2000 символов."
        )
        return

    # Сохраняем сообщение в состоянии
    await state.update_data(
        feedback_message=message.text,
        user_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name
    )

    # Показываем превью сообщения
    user_display = f"@{message.from_user.username}" if message.from_user.username else message.from_user.first_name or f"User {message.from_user.id}"

    preview_text = (
        f"📋 <b>Предварительный просмотр вашего обращения:</b>\n\n"
        f"👤 <b>От:</b> {user_display}\n"
        f"📝 <b>Сообщение:</b>\n{message.text}\n\n"
        f"<i>Так это будет видно администраторам</i>\n\n"
        f"Отправить обращение?"
    )

    # Создаем inline клавиатуру
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да", callback_data="feedback_confirm"),
            InlineKeyboardButton(text="❌ Нет", callback_data="feedback_cancel")
        ]
    ])

    await message.answer(
        preview_text,
        parse_mode="HTML",
        reply_markup=keyboard
    )

    await state.set_state(FeedbackStates.confirming_send)

@feedback_router.callback_query(F.data == "feedback_confirm")
async def confirm_feedback(callback: CallbackQuery, state: FSMContext):
    """Подтверждение отправки обратной связи"""
    print(f"DEBUG: Подтверждение feedback от пользователя {callback.from_user.id}")

    user_data = await state.get_data()

    # Сохраняем в систему хранения
    feedback_id = feedback_manager.add_feedback(
        user_id=user_data["user_id"],
        username=user_data.get("username"),
        first_name=user_data.get("first_name"),
        last_name=user_data.get("last_name"),
        message=user_data["feedback_message"]
    )

    if feedback_id:
        # Отправляем подтверждение пользователю
        await callback.message.edit_text(
            "✅ <b>Обращение отправлено!</b>\n\n"
            f"📋 ID обращения: #{feedback_id}\n"
            "Спасибо за обратную связь! "
            "Администраторы рассмотрят ваше сообщение.",
            parse_mode="HTML"
        )

        print(f"SUCCESS: Новое обращение #{feedback_id} от пользователя {user_data['user_id']}")
    else:
        await callback.message.edit_text(
            "❌ Произошла ошибка при отправке обращения. "
            "Попробуйте позже или обратитесь к администраторам."
        )
        print(f"ERROR: Не удалось сохранить feedback от пользователя {user_data['user_id']}")

    await state.clear()
    await callback.answer()

@feedback_router.callback_query(F.data == "feedback_cancel")
async def cancel_feedback(callback: CallbackQuery, state: FSMContext):
    """Отмена отправки обратной связи"""
    print(f"DEBUG: Отмена feedback от пользователя {callback.from_user.id}")

    await callback.message.edit_text(
        "❌ Отправка обращения отменена.\n\n"
        "Чтобы начать заново, используйте команду /feedback"
    )
    await state.clear()
    await callback.answer()

@feedback_router.message(Command("admin_feedback"))
async def cmd_admin_feedback(message: Message):
    """Просмотр всех обращений обратной связи (только для администраторов)"""
    print(f"DEBUG: Команда /admin_feedback от {message.from_user.username}")

    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    feedbacks = feedback_manager.get_all_feedback(limit=20)
    unread_count = feedback_manager.get_unread_count()

    if not feedbacks:
        await message.answer(
            "📭 <b>Обращений пока нет</b>\n\n"
            "Пользователи еще не отправляли обратную связь.",
            parse_mode="HTML"
        )
        return

    response_text = (
        f"📬 <b>Обращения пользователей</b>\n"
        f"📊 Всего: {len(feedbacks)} | 🔔 Непрочитанных: {unread_count}\n\n"
    )

    for i, feedback in enumerate(feedbacks[:10], 1):  # Показываем только первые 10
        status = "🔴" if not feedback['is_read'] else "✅"
        user_display = feedback.get('username', feedback.get('first_name', f"User {feedback['user_id']}"))
        if feedback.get('username'):
            user_display = f"@{user_display}"

        # Обрезаем длинные сообщения
        message_preview = feedback['message']
        if len(message_preview) > 100:
            message_preview = message_preview[:100] + "..."

        created_at = feedback['created_at'][:16].replace('T', ' ')

        response_text += (
            f"{status} <b>#{feedback['id']}</b> | {user_display}\n"
            f"📅 {created_at}\n"
            f"💬 {message_preview}\n\n"
        )

    if len(feedbacks) > 10:
        response_text += f"... и еще {len(feedbacks) - 10} обращений\n\n"

    response_text += (
        "<i>Используйте /feedback_detail [ID] для просмотра полного текста</i>"
    )

    await message.answer(response_text, parse_mode="HTML")

@feedback_router.message(Command("feedback_detail"))
async def cmd_feedback_detail(message: Message):
    """Просмотр детального обращения (только для администраторов)"""
    if not is_admin(message.from_user.username):
        await message.answer("❌ Эта команда доступна только администраторам.")
        return

    try:
        # Извлекаем ID из команды
        args = message.text.split()
        if len(args) < 2:
            await message.answer("❌ Укажите ID обращения. Пример: /feedback_detail 1")
            return

        feedback_id = int(args[1])
        feedback_data = feedback_manager.get_feedback_by_id(feedback_id)

        if not feedback_data:
            await message.answer(f"❌ Обращение #{feedback_id} не найдено.")
            return

        # Отмечаем как прочитанное
        feedback_manager.mark_as_read(feedback_id)

        user_display = feedback_data.get('username', feedback_data.get('first_name', f"User {feedback_data['user_id']}"))
        if feedback_data.get('username'):
            user_display = f"@{user_display}"

        detail_text = (
            f"📋 <b>Обращение #{feedback_data['id']}</b>\n\n"
            f"👤 <b>От:</b> {user_display}\n"
            f"📅 <b>Дата:</b> {feedback_data['created_at'][:16].replace('T', ' ')}\n"
            f"👁️ <b>Статус:</b> {'Прочитано' if feedback_data['is_read'] else 'Новое'}\n\n"
            f"📝 <b>Сообщение:</b>\n{feedback_data['message']}"
        )

        await message.answer(detail_text, parse_mode="HTML")

    except ValueError:
        await message.answer("❌ Неверный формат ID. Укажите число.")
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении обращения: {e}")
