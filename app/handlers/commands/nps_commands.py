"""
Обработчики NPS (Net Promoter Score) опросов для групповых чатов
"""
from typing import Optional

from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, \
    CallbackQuery
from app.controllers.nps_manager import NPSManager
from app.db import SessionLocal
from app.models.nps_survey import NPSSurvey
from app.utils.decorators import admin_only
from aiogram.filters import Command

from app.utils.tools import escape_markdown

nps_router = Router(name="nps_system")
nps_manager = NPSManager(SessionLocal)


async def send_nps_survey(chat_id: int, trigger_count: int):
    """Отправить NPS опрос в чат (для всех участников)"""
    from app.bot import bot

    # Создаем клавиатуру с оценками 0-10
    keyboard_rows = []
    for i in range(1, 11, 5):  # Разбиваем на строки по 5 кнопок
        row = []
        for score in range(i, min(i + 5, 11)):
            row.append(InlineKeyboardButton(
                text=str(score),
                callback_data=f"nps_score:{score}:{trigger_count}"
            ))
        keyboard_rows.append(row)

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

    text = (
        f"📊 **Короткий опрос для улучшения бота**\n\n"
        f"Насколько вы готовы порекомендовать наш бот друзьям?\n"
        f"Оцените от 1 (совсем не готов) до 10 (обязательно порекомендую)\n\n"
    )

    survey_message = await bot.send_message(
        chat_id=chat_id,
        text=escape_markdown(text),
        reply_markup=markup,
        parse_mode="MarkdownV2"
    )

    ### NPSSurvey должен создавать запись в БД в send_nps_survey
    survey_id = nps_manager.create_survey_record(
        chat_id=chat_id,
        message_id=survey_message.message_id,
        trigger_count=trigger_count
    )
    if survey_id:
        print(f"✅ Создана запись опроса #{survey_id} для чата {chat_id}")
    else:
        print(f"❌ Не удалось сохранить запись опроса для чата {chat_id}")

    return survey_message.message_id

def create_survey_record(
        self, chat_id: int, survey_message_id: int, trigger_count: int
) -> Optional[int]:
    """Создать запись опроса (до получения оценок)"""
    try:
        with self.session_maker() as session:
            survey = NPSSurvey(
                user_id=0,  # ноль или NULL для системной записи
                chat_id=chat_id,
                username=None,
                score=-1,  # временно «нет оценки»
                trigger_count=trigger_count,
                survey_message_id=survey_message_id
            )
            session.add(survey)
            session.commit()
            return survey.id
    except Exception as e:
        print(f"❌ Ошибка создания записи опроса: {e}")
        return None

@nps_router.callback_query(F.data.startswith("nps_score:"))
async def handle_nps_response(callback: CallbackQuery):
    """Обработка NPS оценки"""
    try:
        # Парсим callback data: nps_score:score:trigger_count
        parts = callback.data.split(":")
        if len(parts) != 3:
            await callback.answer("Неверный формат данных")
            return

        score = int(parts[1])
        trigger_count = int(
            parts[2])  # Это количество триггеров на момент создания опроса

        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id

        # Проверяем, может ли пользователь отвечать
        if not nps_manager.can_user_respond(user_id, chat_id):
            await callback.answer("Вы уже отвечали на опрос в последнее время",
                                  show_alert=True)
            return

        # Сохраняем NPS ответ
        nps_id = nps_manager.add_nps_response(
            user_id=user_id,
            chat_id=chat_id,
            score=score,
            trigger_count=trigger_count,
            message_id=message_id,
            username=callback.from_user.username
        )

        if not nps_id:
            await callback.answer("Ошибка сохранения ответа", show_alert=True)
            return

        # Определяем персональный ответ в зависимости от оценки
        if score >= 9:  # Promoters
            personal_response = (
                f"✅ Спасибо за высокую оценку {score}/10! "
                "Рады, что вам нравится наш бот! "
                "Если хотите предложить новые фичи — используйте /feedback."
            )
        elif score >= 7:  # Passives
            personal_response = (
                f"👍 Спасибо за оценку {score}/10! "
                "Если есть идеи, как нам стать лучше — напишите через /feedback."
            )
        else:  # Detractors
            personal_response = (
                f"😔 Спасибо за честную оценку {score}/10. "
                "Нам важно понять, что не устраивает. "
                "Опишите проблемы через /feedback — обязательно все исправим!"
            )

        # Отправляем персональный ответ
        await callback.answer(personal_response, show_alert=True)

        # НЕ сбрасываем счетчик здесь - он уже сброшен при отправке опроса

    except Exception as e:
        print(f"❌ Ошибка в handle_nps_response: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)


# Админские команды
@nps_router.message(Command("nps_stats"))
@admin_only
async def cmd_nps_stats(message: Message):
    """Общая статистика NPS"""
    stats = nps_manager.get_nps_stats(days=30)

    if stats["total_responses"] == 0:
        text = "📊 **NPS Статистика**\n\nОтветов пока нет"
    else:
        text = (
            f"📊 **NPS Статистика (30 дней)**\n\n"
            f"🎯 **NPS Score:** {stats['nps_score']}\n"
            f"📝 **Всего ответов:** {stats['total_responses']}\n"
            f"🟢 **Промоутеры (9-10):** {stats['promoters']}\n"
            f"🟡 **Пассивные (7-8):** {stats['passives']}\n"
            f"🔴 **Критики (0-6):** {stats['detractors']}"
        )

    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")
