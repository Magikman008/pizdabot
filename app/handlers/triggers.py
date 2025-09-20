from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import re

from app.controllers import user_trigger_manager, chat_settings_manager, bot_stats
from app.states import FeedbackStates
from triggers import russian_swear_triggers

base_trigger_router = Router()


def is_caps_message(text):
    if not text:
        return False

    # Убираем пунктуацию и пробелы для анализа
    clean_text = re.sub(r'[^\w\u0400-\u04FF]', '', text, flags=re.UNICODE)

    # Если после очистки нет букв, возвращаем False
    if not clean_text:
        return False

    # Проверяем, что все буквы в верхнем регистре
    return clean_text.isupper()


@base_trigger_router.message(F.text, ~F.text.startswith(("/")))
async def handle_triggers(message: Message, state: FSMContext):
    if not message.text:
        return

    # КРИТИЧЕСКИ ВАЖНО: Проверяем, не находится ли пользователь в процессе обратной связи
    current_state = await state.get_state()
    if current_state in [
        FeedbackStates.waiting_for_message.state,
        FeedbackStates.confirming_send.state,
    ]:
        print(
            f"⏭️ Пропускаем триггеры для пользователя {message.from_user.id} - в процессе feedback"
        )
        return  # НЕ обрабатываем триггеры во время процесса обратной связи

    # ПРОВЕРЯЕМ НАСТРОЙКИ ЧАТА - должен ли бот отвечать
    if not chat_settings_manager.should_respond(message.chat.id):
        return  # Бот выключен или не прошла проверка вероятности

    # НОВОЕ: Определяем, написано ли сообщение КАПСЛОКОМ
    is_caps = is_caps_message(message.text)

    # Приводим сообщение к нижнему регистру для поиска
    text = message.text.lower().strip()

    # Убираем знаки препинания в конце
    text = text.rstrip(".,!?;:")

    # СНАЧАЛА проверяем пользовательские триггеры (они имеют приоритет)
    user_response = user_trigger_manager.get_response(message.chat.id, text)
    if user_response:
        # НОВОЕ: если исходное сообщение КАПСЛОКОМ, отвечаем КАПСЛОКОМ
        response = user_response.upper() if is_caps else user_response
        await message.answer(response)
        return

    # Если пользовательские триггеры не сработали, проверяем глобальные
    # Сортируем триггеры по убыванию длины (сначала более длинные)
    sorted_triggers = sorted(
        russian_swear_triggers.items(), key=lambda x: len(x[0]), reverse=True
    )

    for trigger, response in sorted_triggers:
        trigger_lower = trigger.lower()

        # Проверяем, заканчивается ли сообщение этим триггером
        if text.endswith(trigger_lower):
            # Дополнительная проверка: триггер должен быть отдельным словом/фразой
            # (не частью другого слова)
            if (
                    len(text) == len(trigger_lower)
                    or text[-(len(trigger_lower) + 1)] in " .,!?;:"
            ):
                # НОВОЕ: если исходное сообщение КАПСЛОКОМ, отвечаем КАПСЛОКОМ
                final_response = response.upper() if is_caps else response
                await message.answer(final_response)
                # Записываем статистику
                bot_stats.add_roast(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    trigger=trigger,
                )
                return  # Отвечаем только на первый найденный триггер
