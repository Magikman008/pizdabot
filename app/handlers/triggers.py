from aiogram import F, Router
from aiogram.types import Message

from app.chat_settings import chat_settings_manager
from app.statistics import bot_stats
from app.user_triggers import user_trigger_manager
from triggers import russian_swear_triggers

base_trigger_router = Router()


@base_trigger_router.message(F.text, ~F.text.startswith(("/")))
async def handle_triggers(message: Message):
    """
    Обработка триггеров в конце сообщений
    Сначала проверяет настройки чата, потом пользовательские триггеры, потом глобальные
    """
    if not message.text:
        return

    # ПРОВЕРЯЕМ НАСТРОЙКИ ЧАТА - должен ли бот отвечать
    if not chat_settings_manager.should_respond(message.chat.id):
        return  # Бот выключен или не прошла проверка вероятности

    # Приводим сообщение к нижнему регистру для поиска
    text = message.text.lower().strip()

    # Убираем знаки препинания в конце
    text = text.rstrip(".,!?;:")

    # СНАЧАЛА проверяем пользовательские триггеры (они имеют приоритет)
    user_response = user_trigger_manager.get_response(message.chat.id, text)
    if user_response:
        await message.answer(user_response)
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
                # Записываем статистику
                bot_stats.add_roast(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    trigger=trigger,
                )
                await message.answer(response)
                return  # Отвечаем только на первый найденный триггер
