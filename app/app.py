# Обновленный app.py с интеграцией Telegram Stars подписок

import logging
import re
import json
from io import BytesIO

from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, BufferedInputFile, CallbackQuery, LabeledPrice, PreCheckoutQuery
from aiogram.filters import Command


import settings
from triggers import russian_swear_triggers
from app.statistics import bot_stats
from app.user_triggers import user_trigger_manager
from app.chat_settings import chat_settings_manager
from app.subscription_manager import subscription_manager

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
bot = Bot(token=settings.token)
dp = Dispatcher()
commands_router = Router()  # Роутер для команд
triggers_router = Router()  # Роутер для триггеров
callback_router = Router()  # Роутер для callback запросов
payment_router = Router()  # Роутер для платежей

# Список администраторов по username
ADMIN_USERNAMES = ['dunda2', 'window_exit']


def is_admin(message: Message) -> bool:
    """Проверка, является ли пользователь администратором"""
    return message.from_user.username in ADMIN_USERNAMES


def has_premium_access(user_id: int) -> bool:
    """Проверка наличия премиум-доступа у пользователя"""
    return subscription_manager.has_active_subscription(user_id)


# Обработчик для всех текстовых сообщений
@triggers_router.message(F.text)
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
    text = text.rstrip('.,!?;:')

    # СНАЧАЛА проверяем пользовательские триггеры (они имеют приоритет)
    user_response = user_trigger_manager.get_response(message.chat.id, text)
    if user_response:
        await message.answer(user_response)
        return

    # Если пользовательские триггеры не сработали, проверяем глобальные
    # Сортируем триггеры по убыванию длины (сначала более длинные)
    sorted_triggers = sorted(russian_swear_triggers.items(), key=lambda x: len(x[0]),
                             reverse=True)

    for trigger, response in sorted_triggers:
        trigger_lower = trigger.lower()

        # Проверяем, заканчивается ли сообщение этим триггером
        if text.endswith(trigger_lower):
            # Дополнительная проверка: триггер должен быть отдельным словом/фразой
            # (не частью другого слова)
            if len(text) == len(trigger_lower) or text[
                -(len(trigger_lower) + 1)] in ' .,!?;:':
                # Записываем статистику
                bot_stats.add_roast(
                    user_id=message.from_user.id,
                    chat_id=message.chat.id,
                    trigger=trigger
                )
                await message.answer(response)
                return  # Отвечаем только на первый найденный триггер


# =========================
# ПОДПИСКИ ЧЕРЕЗ TELEGRAM STARS
# =========================

@commands_router.message(Command("sub"))
async def show_subscription_info(message: Message):
    """Показать информацию о подписке и возможность покупки"""
    description = subscription_manager.get_subscription_description()
    keyboard = subscription_manager.create_subscription_keyboard()

    await message.answer(description, reply_markup=keyboard)


@callback_router.callback_query(F.data.startswith("buy_subscription:"))
async def process_subscription_purchase(callback: CallbackQuery):
    """Обработка покупки подписки за звёздочки"""
    await callback.answer()

    try:
        # Извлекаем цену из callback_data
        _, price_str = callback.data.split(":")
        price_stars = int(price_str)

        # Создаем инвойс для оплаты звёздочками
        prices = [LabeledPrice(label="Премиум подписка", amount=price_stars)]

        # Отправляем инвойс пользователю
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title="⭐ Премиум-подписка PizdaBot",
            description=f"Подписка на {subscription_manager.SUBSCRIPTION_DURATION_DAYS} дней с премиум-функциями",
            payload=f"subscription:{callback.from_user.id}:{price_stars}",
            provider_token="",  # Для звёздочек пустой
            currency="XTR",  # Валюта звёздочек
            prices=prices,
            need_name=False,
            need_phone_number=False,
            need_email=False,
            need_shipping_address=False,
            send_phone_number_to_provider=False,
            send_email_to_provider=False,
            is_flexible=False,
        )

        await callback.message.answer(
            "💫 Инвойс для оплаты отправлен! Проверьте личные сообщения с ботом."
        )

    except Exception as e:
        logger.error(f"Ошибка при создании инвойса: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при создании платежа. Попробуйте позже."
        )


@callback_router.callback_query(F.data == "subscription_info")
async def show_subscription_status(callback: CallbackQuery):
    """Показать статус подписки пользователя"""
    await callback.answer()

    sub_info = subscription_manager.get_subscription_info(callback.from_user.id)
    await callback.message.answer(sub_info)


@payment_router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre-checkout запроса"""
    # Проверяем payload
    if pre_checkout_query.invoice_payload.startswith("subscription:"):
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(
            ok=False,
            error_message="Неверный тип платежа"
        )


@payment_router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешного платежа"""
    payment = message.successful_payment

    # Проверяем, что это платеж за подписку
    if payment.invoice_payload.startswith("subscription:"):
        try:
            _, user_id_str, price_str = payment.invoice_payload.split(":")
            user_id = int(user_id_str)

            # Активируем подписку
            success, msg = subscription_manager.activate_subscription(
                user_id=user_id,
                transaction_id=payment.telegram_payment_charge_id
            )

            if success:
                await message.answer(msg)

                # Уведомляем админов о новой подписке (опционально)
                admin_msg = f"🎉 Новая подписка!\nПользователь: {message.from_user.full_name} (ID: {user_id})\nОплата: {payment.total_amount} звёздочек"
                for admin_username in ADMIN_USERNAMES:
                    try:
                        # Здесь можно отправить уведомление админам
                        pass
                    except:
                        pass
            else:
                await message.answer(
                    "❌ Ошибка при активации подписки. Обратитесь к администратору.")

        except Exception as e:
            logger.error(f"Ошибка при обработке платежа: {e}")
            await message.answer("❌ Произошла ошибка при обработке платежа.")


@commands_router.message(Command("premium"))
async def premium_command(message: Message):
    """Премиум-команда доступная только подписчикам"""
    if not has_premium_access(message.from_user.id):
        await message.answer(
            "⭐ Эта команда доступна только премиум-пользователям!\n\n"
            "Используйте /sub для покупки подписки."
        )
        return

    premium_info = """🌟 **Премиум-функции активированы!**

🎯 Доступные возможности:
• Расширенная статистика
• Увеличенные лимиты на триггеры  
• Приоритетная обработка
• Эксклюзивные команды
• Техническая поддержка

✨ Спасибо за поддержку проекта!"""

    await message.answer(premium_info)


# =========================
# КОМАНДЫ УПРАВЛЕНИЯ БОТОМ В ЧАТЕ
# =========================

@commands_router.message(Command("off"))
async def turn_bot_off(message: Message):
    """Выключить бота в чате"""
    success, msg = chat_settings_manager.set_bot_enabled(
        chat_id=message.chat.id,
        enabled=False,
        user_id=message.from_user.id
    )
    await message.answer(msg)


@commands_router.message(Command("on"))
async def turn_bot_on(message: Message):
    """Включить бота в чате"""
    success, msg = chat_settings_manager.set_bot_enabled(
        chat_id=message.chat.id,
        enabled=True,
        user_id=message.from_user.id
    )
    await message.answer(msg)


@commands_router.message(Command("chance"))
async def set_response_chance(message: Message):
    """Установить вероятность ответа бота"""
    if not message.text:
        return

    # Парсим команду для извлечения числа
    pattern = r'/chance\s+(\d+)'
    match = re.match(pattern, message.text)

    if not match:
        await message.answer(
            '❌ Неправильный формат команды!\n\n'
            'Используйте: /chance <число от 0 до 100>\n'
            'Примеры:\n'
            '/chance 50 - бот отвечает в 50% случаев\n'
            '/chance 0 - бот не отвечает\n'
            '/chance 100 - бот отвечает всегда'
        )
        return

    try:
        chance = int(match.group(1))
    except ValueError:
        await message.answer("❌ Введите корректное число от 0 до 100!")
        return

    success, msg = chat_settings_manager.set_response_chance(
        chat_id=message.chat.id,
        chance=chance,
        user_id=message.from_user.id
    )
    await message.answer(msg)


@commands_router.message(Command("settings"))
async def show_chat_settings(message: Message):
    """Показать текущие настройки чата"""
    settings_info = chat_settings_manager.get_chat_info(message.chat.id)
    await message.answer(settings_info)


@commands_router.message(Command("reset_settings"))
async def reset_chat_settings(message: Message):
    """Сбросить настройки чата (только админы)"""
    if not is_admin(message):
        await message.answer("❌ Эта команда доступна только администраторам!")
        return

    success, msg = chat_settings_manager.reset_chat_settings(
        chat_id=message.chat.id,
        user_id=message.from_user.id
    )
    await message.answer(msg)


# =========================
# КОМАНДЫ ПОЛЬЗОВАТЕЛЬСКИХ ТРИГГЕРОВ
# =========================

@commands_router.message(Command("add"))
async def add_trigger(message: Message):
    """Добавить пользовательский триггер (ТОЛЬКО для подписчиков)"""
    if not message.text:
        return

    # ПРОВЕРЯЕМ ПОДПИСКУ ПЕРВЫМ ДЕЛОМ
    if not has_premium_access(message.from_user.id):
        keyboard = subscription_manager.create_subscription_keyboard()
        await message.answer(
            "⭐ **Добавление триггеров доступно только подписчикам!**\n\n"
            f"Купите премиум-подписку за {subscription_manager.SUBSCRIPTION_PRICE_STARS} звёздочку чтобы добавлять свои триггеры:",
            reply_markup=keyboard
        )
        return

    # Увеличиваем лимиты для премиум-пользователей
    user_trigger_manager.MAX_TRIGGERS_PER_USER_PER_DAY = 10
    user_trigger_manager.MAX_TRIGGERS_PER_CHAT = 100

    # Парсим команду с помощью регулярного выражения для извлечения "фраза" "ответ"
    pattern = r'/add\s+"([^"]+)"\s+"([^"]+)"'
    match = re.match(pattern, message.text)

    if not match:
        await message.answer(
            '❌ Неправильный формат команды!\n\n'
            'Используйте: /add "фраза" "ответ"\n'
            'Пример: /add "привет" "и тебе привет!"'
        )
        return

    trigger, response = match.groups()

    success, msg = user_trigger_manager.add_trigger(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        trigger=trigger,
        response=response
    )

    # Добавляем информацию о премиум-статусе
    if success:
        msg += "\n\n⭐ Премиум-пользователь: увеличенные лимиты активны!"

    await message.answer(msg)


@commands_router.message(Command("remove"))
async def remove_trigger(message: Message):
    """Удалить пользовательский триггер"""
    if not message.text:
        return

    # Парсим команду для извлечения "фраза"
    pattern = r'/remove\s+"([^"]+)"'
    match = re.match(pattern, message.text)

    if not match:
        await message.answer(
            '❌ Неправильный формат команды!\n\n'
            'Используйте: /remove "фраза"\n'
            'Пример: /remove "привет"'
        )
        return

    trigger = match.groups()[0]

    success, msg = user_trigger_manager.remove_trigger(
        user_id=message.from_user.id,
        chat_id=message.chat.id,
        trigger=trigger,
        is_admin=is_admin(message)
    )

    await message.answer(msg)


@commands_router.message(Command("triggers"))
async def list_triggers(message: Message):
    """Показать все триггеры чата"""
    triggers_list = user_trigger_manager.list_chat_triggers(message.chat.id)
    await message.answer(triggers_list)


@commands_router.message(Command("my_triggers"))
async def my_triggers_stats(message: Message):
    """Показать статистику пользователя по триггерам"""
    stats = user_trigger_manager.get_user_stats(message.from_user.id)

    # Добавляем информацию о премиум-статусе
    if has_premium_access(message.from_user.id):
        stats += "\n\n⭐ **Премиум-статус активен!**\n• Увеличенные лимиты на триггеры\n• Приоритетная обработка"

    await message.answer(stats)


# =========================
# КОМАНДЫ СТАТИСТИКИ
# =========================

@commands_router.message(Command("stats"))
async def show_stats(message: Message):
    """Показать общую статистику бота"""
    stats_text = bot_stats.get_stats_summary()
    await message.answer(stats_text)


@commands_router.message(Command("top"))
async def show_top_triggers(message: Message):
    """Показать топ триггеров"""
    top = bot_stats.get_top_triggers(10)
    if not top:
        await message.answer("📊 Пока нет статистики по триггерам")
        return

    text = "🏆 Топ-10 триггеров:\n\n"
    for i, (trigger, count) in enumerate(top.items(), 1):
        text += f"{i}. '{trigger}' - {count} раз\n"

    await message.answer(text)


@commands_router.message(Command("today"))
async def show_today_stats(message: Message):
    """Показать статистику за сегодня"""
    today = bot_stats.get_daily_stats()

    text = f"""📅 Статистика за сегодня ({today['date']})

🔥 Подъёбов: {today['roasts']}
👥 Пользователей: {today['unique_users']}
💬 Групп: {today['unique_groups']}"""

    await message.answer(text)


# =========================
# АДМИНСКИЕ КОМАНДЫ
# =========================

@commands_router.message(Command("admin_stats"))
async def admin_stats(message: Message):
    """Детальная статистика (только для админов)"""
    if not is_admin(message):
        # Не отвечаем обычным пользователям - скрываем команду
        return

    detailed_stats = bot_stats.get_detailed_stats()

    # Добавляем информацию о подписчиках
    subscribers = subscription_manager.get_all_subscribers()
    detailed_stats += f"\n\n⭐ Активных подписчиков: {len(subscribers)}"

    await message.answer(detailed_stats)


@commands_router.message(Command("export_stats"))
async def export_stats(message: Message):
    """Экспорт статистики в JSON файл (только для админов)"""
    if not is_admin(message):
        # Не отвечаем обычным пользователям - скрываем команду
        return

    try:
        stats_data = bot_stats.export_stats()
        json_data = json.dumps(stats_data, ensure_ascii=False, indent=2)

        # Создаем файл в памяти
        file_buffer = BytesIO(json_data.encode('utf-8'))
        input_file = BufferedInputFile(
            file_buffer.getvalue(),
            filename="bot_stats_export.json"
        )

        await message.answer_document(
            input_file,
            caption="📊 Экспорт статистики бота"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при экспорте: {str(e)}")


@commands_router.message(Command("clear_stats"))
async def clear_stats(message: Message):
    """Очистить статистику (только для админов)"""
    if not is_admin(message):
        # Не отвечаем обычным пользователям - скрываем команду
        return

    bot_stats.clear_stats()
    await message.answer(
        "🗑️ Статистика очищена!\n\nВся статистика была сброшена до нуля.")


@commands_router.message(Command("remove_all_triggers"))
async def remove_all_triggers(message: Message):
    """Удалить все пользовательские триггеры чата (только для админов)"""
    if not is_admin(message):
        return

    chat_str = str(message.chat.id)
    if chat_str in user_trigger_manager.data["chat_triggers"]:
        user_trigger_manager.data["chat_triggers"][chat_str] = {}
        user_trigger_manager._save_triggers()
        await message.answer("🗑️ Все пользовательские триггеры чата удалены!")
    else:
        await message.answer("❌ В этом чате нет пользовательских триггеров")


@commands_router.message(Command("subscribers"))
async def show_subscribers(message: Message):
    """Показать список подписчиков (только для админов)"""
    if not is_admin(message):
        return

    subscribers = subscription_manager.get_all_subscribers()

    if not subscribers:
        await message.answer("📋 Активных подписчиков нет")
        return

    text = f"👥 **Активные подписчики ({len(subscribers)}):**\n\n"

    for i, (user_str, sub_data) in enumerate(subscribers.items(), 1):
        expires_at = sub_data.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = expires_at[:16]  # Обрезаем до даты и времени
        text += f"{i}. ID: {user_str} (до {expires_at})\n"

    await message.answer(text)


# =========================
# СПРАВКА И ПРИВЕТСТВИЕ
# =========================

@commands_router.message(Command("help"))
async def show_help(message: Message):
    """Показать список команд (разный для админов и обычных пользователей)"""

    # Обычные команды для всех
    help_text = """🤖 Команды бота:

⚙️ Управление ботом:
/on - включить бота в чате
/off - выключить бота в чате
/chance <0-100> - вероятность ответа (%)
/settings - текущие настройки чата

⭐ Подписка:
/sub - купить премиум-подписку за 1 звёздочку
/premium - премиум-функции (только для подписчиков)

📊 Статистика:
/stats - общая статистика
/top - топ триггеров
/today - статистика за сегодня

🎯 Пользовательские триггеры:
/add "фраза" "ответ" - добавить триггер
/remove "фраза" - удалить свой триггер
/triggers - список триггеров чата
/my_triggers - ваша статистика

/help - эта справка"""

    # Для админов добавляем админские команды
    if is_admin(message):
        help_text += """

👑 Админские команды:
/admin_stats - детальная статистика
/export_stats - экспорт в JSON
/clear_stats - очистить статистику
/remove_all_triggers - удалить все триггеры чата
/reset_settings - сбросить настройки чата
/subscribers - список подписчиков"""

    help_text += "\n\n📝 Просто пишите фразы, и я буду отвечать! 😄"
    help_text += "\n\n💡 Пользовательские триггеры имеют приоритет над глобальными."
    help_text += "\n\n🎲 Используйте /chance для настройки частоты ответов!"
    help_text += "\n\n⭐ Поддержите проект подпиской - /sub!"

    await message.answer(help_text)


@commands_router.message(Command("start"))
async def start_command(message: Message):
    """Команда start для приветствия"""
    welcome_text = """👋 Добро пожаловать в PizdaBot!

Я отвечаю на различные фразы забавными ответами.

🎯 Теперь вы можете добавлять свои собственные триггеры командой:
/add "фраза" "ответ"

⚙️ Управляйте ботом:
/off - выключить бота в чате
/on - включить бота обратно
/chance 50 - ответы в 50% случаев

⭐ Новинка! Премиум-подписка:
/sub - купить подписку за 1 звёздочку Telegram
• Увеличенные лимиты на триггеры
• Эксклюзивные функции
• Приоритетная обработка

📋 Используйте /help чтобы посмотреть все команды.

Просто напишите что-нибудь и посмотрите что получится! 😄"""

    await message.answer(welcome_text)


async def main():
    # Подключаем роутеры в правильном порядке
    dp.include_router(commands_router)  # Команды первыми
    dp.include_router(callback_router)  # Callback запросы
    dp.include_router(payment_router)  # Платежи
    dp.include_router(triggers_router)  # Триггеры последними

    # Очищаем истёкшие подписки при запуске
    subscription_manager.cleanup_expired_subscriptions()

    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())