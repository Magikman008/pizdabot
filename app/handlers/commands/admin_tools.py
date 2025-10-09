import logging
from datetime import datetime

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.controllers import admin_notifier, chat_info_manager
from app.controllers import bot_stats, subscription_manager
from app.controllers import feedback_manager
from app.models.chat_info import ChatInfo
from app.services import scheduler_service
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
        if fb.username:
            user_display = f"@{user_display}"

        message_preview = fb.message
        if len(message_preview) > 150:
            message_preview = message_preview[:150] + "..."

        created_at = fb.created_at.strftime("%d.%m.%y")

        text += (
            f"🆔 **#{fb.id}** | {user_display}\n"
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
            "Пользователи еще не отправляли обратную связь."
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
• `/admin_stats` - детальная статистика бота с информацией по пользователям
• `/subscribers` - показать список активных подписчиков
• `/nps_stats` - статистика по опросам Net Promoter Score

🗑 **Управление данными:**   
• `/reset_settings` - сбросить настройки чата к значениям по умолчанию

💬 **Управление чатами:**
• `/update_chats` - обновить информацию о всех чатах бота
• `/show_chats` - показать список всех чатов с подробной информацией
• `/chat_analytics [chat_id] [days]` - аналитика конкретного чата
• `/growth_charts [days]` - графики роста количества групп и участников

🤖 **Системные команды:**
• `/scheduler_status` - статус планировщика задач и активных заданий

📝 **Система обратной связи:**
• `/admin_register` - регистрация для получения уведомлений о новых обращениях
• `/admin_feedback` - просмотр всех обращений пользователей
• `/feedback_unread` - показать только непрочитанные обращения
• `/feedback_detail <ID>` - детальный просмотр обращения по ID
• `/feedback_stats` - статистика по обращениям с аналитикой
• `/feedback_mark_all_read` - отметить все обращения как прочитанные
• `/feedback_delete <ID>` - удалить конкретное обращение
• `/feedback_user <user_id>` - все обращения конкретного пользователя

ℹ️ **Справка:**
• `/admin_help` - эта справка по административным командам

📋 **Примеры использования:**
• `/chat_analytics -123456789 30` - аналитика чата за 30 дней
• `/growth_charts 90` - графики за 90 дней
• `/feedback_detail 42` - просмотр обращения №42
• `/feedback_user 123456789` - обращения пользователя"""

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

        if stats["errors"] > 0:
            report += "\n\n⚠️ *Подробности ошибок смотрите в логах бота*"

        if stats["deactivated"] > 0:
            report += f"\n\n📝 *{stats['deactivated']} чатов помечено как неактивных (бот удален)*"

        await status_msg.edit_text(report, parse_mode="Markdown")

    except Exception as e:
        error_msg = f"❌ **Ошибка при обновлении чатов**\n\n🔍 Детали: `{str(e)}`"
        await status_msg.edit_text(error_msg, parse_mode="Markdown")


@admin_router.message(Command("show_chats"))
@admin_only
async def show_chats_command(message: Message):
    """Команда для просмотра всех чатов, корректно обрабатывает любые null значения из БД"""

    try:
        chats_info = await get_all_chats_info()

        if not chats_info:
            await message.reply("📭 Чатов не найдено")
            return

        response = "📋 **Все чаты бота:**\n\n"

        for i, chat in enumerate(chats_info, 1):
            # Дефолтные значения для возможных None
            title = chat.chat_title or "—"
            title = (title[:30] + "...") if len(title) > 30 else title

            description = chat.chat_description or ""
            if description:
                description = (description[:50] + "...") if len(description) > 50 else description
            else:
                description = "—"

            added_date = (
                chat.added_at.strftime("%d.%m.%Y %H:%M")
                if getattr(chat, "added_at", None)
                else "—"
            )

            added_by = chat.added_by_username or "неизвестно"

            members = chat.members_count if chat.members_count is not None else "—"

            is_active = bool(getattr(chat, "is_active", False))
            status_emoji = "✅" if is_active else "❌"
            status_text = "активен" if is_active else "неактивен"

            chat_type_raw = chat.chat_type or ""
            chat_type_map = {
                "private": "👤 Личный",
                "group": "👥 Группа",
                "supergroup": "👥 Супергруппа",
                "channel": "📢 Канал",
            }
            chat_type_str = chat_type_map.get(chat_type_raw, chat_type_raw or "—")

            response += (
                f"**{i}. {title}**\n"
                f"{chat_type_str} | {members} чел.\n"
                f"📅 Добавлен: {added_date}\n"
                f"👤 Кем: @{added_by}\n"
                f"📝 Описание: {description}\n"
                f"🤖 Бот: {status_emoji} {status_text}\n\n"
            )

        # Разбивка длинного сообщения по лимиту Telegram
        if len(response) > 4000:
            parts = split_long_message(response, 4000)
            for part in parts:
                await message.reply(part, parse_mode="Markdown")
        else:
            await message.reply(response, parse_mode="Markdown")

    except Exception as e:
        await message.reply(f"❌ Ошибка при получении списка чатов: {e}")
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


@admin_router.message(Command("scheduler_status"))
@admin_only
async def scheduler_status_command(message: Message):
    """Статус планировщика задач"""
    if scheduler_service.scheduler.running:
        jobs = scheduler_service.scheduler.get_jobs()
        text = f"✅ **Планировщик активен**\n\n"
        text += f"📋 Активных задач: {len(jobs)}\n\n"

        for job in jobs:
            next_run = (
                job.next_run_time.strftime("%H:%M:%S %d.%m.%Y")
                if job.next_run_time
                else "—"
            )
            text += f"🔄 {job.id}\n📅 Следующий запуск: {next_run}\n\n"
    else:
        text = "❌ **Планировщик не активен**"

    await message.answer(escape_markdown(text), parse_mode="MarkdownV2")


@admin_router.message(Command("chat_analytics"))
@admin_only
async def chat_analytics_command(message: Message):
    """Аналитика по чатам"""
    try:
        args = message.text.split()
        chat_id = int(args[1]) if len(args) > 1 else message.chat.id
        days = int(args[2]) if len(args) > 2 else 7

        analytics = await chat_info_manager.get_chat_analytics(chat_id, days)

        if analytics and "error" not in analytics:
            text = f"📊 **Аналитика чата {chat_id}**\n\n"
            text += f"📅 Период: {days} дней\n"
            text += f"📸 Снапшотов: {analytics['snapshots_count']}\n"

            if analytics["snapshots_count"] > 0:
                text += (
                    f"📝 Текущее название: {analytics.get('current_title', 'Н/Д')}\n"
                )
                text += f"👥 Участников: {analytics.get('current_members', 'Н/Д')}\n"
                text += f"🤖 Статус бота: {analytics.get('current_status', 'Н/Д')}\n"
                text += f"✅ Активен: {'Да' if analytics.get('is_active') else 'Нет'}\n"
        else:
            text = "❌ Аналитика недоступна"

        await message.answer(escape_markdown(text), parse_mode="MarkdownV2")

    except (ValueError, IndexError):
        await message.answer(
            "❌ Использование: /chat_analytics [chat_id] [days]\nПример: /chat_analytics -123456789 7"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")


@admin_router.message(Command("growth_charts"))
@admin_only
async def growth_charts_command(message: Message):
    """Графики роста количества групп и участников"""
    try:
        args = message.text.split()
        days = int(args[1]) if len(args) > 1 else 30

        if days > 365:
            await message.answer("❌ Максимальный период: 365 дней")
            return

        # Получаем данные для графиков
        analytics = await chat_info_manager.get_growth_analytics(days)

        if "error" in analytics:
            await message.answer(f"❌ {analytics['error']}")
            return

        if analytics["snapshots_count"] == 0:
            await message.answer("📭 Нет данных для построения графиков")
            return

        # Отправляем статус
        status_msg = await message.reply(
            f"📊 Строим графики за {days} дней...\n"
            f"📸 Снапшотов: {analytics['snapshots_count']}"
        )

        from app.utils.chart_creator import create_growth_chart, create_comparison_chart

        # Подготавливаем данные
        groups_data = []
        members_data = []

        for point in analytics["timeline_data"]:
            groups_data.append({"date": point["date"], "count": point["groups_count"]})
            members_data.append(
                {"date": point["date"], "count": point["total_members"]}
            )

        # Создаем и отправляем график групп
        try:
            groups_chart = await create_growth_chart(
                {
                    "title": f"Рост количества групп за {days} дней",
                    "data": groups_data,
                    "y_label": "Количество групп",
                    "color": "#2196F3",
                }
            )

            await message.answer_photo(
                groups_chart, caption="📊 График роста количества групп"
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка создания графика групп: {str(e)}")

        # Создаем и отправляем график участников
        try:
            members_chart = await create_growth_chart(
                {
                    "title": f"Рост количества участников за {days} дней",
                    "data": members_data,
                    "y_label": "Количество участников",
                    "color": "#4CAF50",
                }
            )

            await message.answer_photo(
                members_chart, caption="👥 График роста количества участников"
            )
        except Exception as e:
            await message.answer(f"❌ Ошибка создания графика участников: {str(e)}")

        # Итоговая статистика
        final_stats = (
            analytics["timeline_data"][-1] if analytics["timeline_data"] else {}
        )

        summary = f"""📈 Аналитика за {days} дней

📊 Текущие показатели:
👥 Групп: {final_stats.get('groups_count', 0)}
🧑‍🤝‍🧑 Участников: {final_stats.get('total_members', 0):,}
💬 Приватных чатов: {final_stats.get('private_chats', 0)}

📅 {analytics['date_range']['from']} — {analytics['date_range']['to']}"""

        await status_msg.edit_text(summary)

    except ValueError:
        await message.answer(
            "❌ Использование: /growth_charts [дни]\nПример: /growth_charts 30"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
