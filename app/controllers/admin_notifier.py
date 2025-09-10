"""
Модуль для отправки уведомлений администраторам
"""
from typing import List, Dict, Any
from app.bot import bot
from settings import ADMIN_USERNAMES


class AdminNotifier:
    """Класс для отправки уведомлений администраторам"""

    def __init__(self):
        # Словарь для хранения chat_id администраторов
        # В реальном проекте лучше хранить это в базе данных
        self.admin_chat_ids: Dict[str, int] = {}

    def register_admin(self, username: str, chat_id: int):
        """
        Зарегистрировать chat_id администратора

        Args:
            username: Username администратора (без @)
            chat_id: Telegram chat_id администратора
        """
        self.admin_chat_ids[username] = chat_id
        print(f"Зарегистрирован админ @{username} с chat_id {chat_id}")

    async def notify_new_feedback(self, feedback_id: int, user_display: str,
                                  message_preview: str):
        """
        Отправить уведомление администраторам о новом обращении

        Args:
            feedback_id: ID обращения
            user_display: Отображаемое имя пользователя
            message_preview: Превью сообщения
        """
        if not ADMIN_USERNAMES:
            print("WARNING: Список ADMIN_USERNAMES пустой, уведомления не отправляются")
            return

        notification_text = (
            f"🔔 **Новое обращение #{feedback_id}**\n\n"
            f"👤 **От:** {user_display}\n"
            f"💬 **Сообщение:**\n{message_preview}\n\n"
            f"*Используйте /feedback_detail {feedback_id} для просмотра*"
        )

        successful_notifications = 0

        for admin_username in ADMIN_USERNAMES:
            try:
                chat_id = self.admin_chat_ids.get(admin_username)
                if chat_id:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=notification_text,
                        parse_mode="HTML"
                    )
                    successful_notifications += 1
                    print(f"✅ Уведомление отправлено админу @{admin_username}")
                else:
                    print(f"⚠️ Не найден chat_id для админа @{admin_username}")
                    # Пишем в лог для отладки
                    print(f"NOTIFICATION for @{admin_username}: {notification_text}")

            except Exception as e:
                print(f"❌ Ошибка отправки уведомления админу @{admin_username}: {e}")

        print(
            f"📊 Отправлено уведомлений: {successful_notifications}/{len(ADMIN_USERNAMES)}")

    async def notify_feedback_stats(self, stats: Dict[str, Any]):
        """
        Отправить статистику по обращениям администраторам

        Args:
            stats: Словарь со статистикой
        """
        stats_text = (
            f"📊 **Еженедельная статистика обращений**\n\n"
            f"📝 Всего обращений: {stats['total_count']}\n"
            f"🔴 Непрочитанных: {stats['unread_count']}\n"
            f"✅ Прочитанных: {stats['read_count']}\n"
            f"👥 Уникальных пользователей: {stats['unique_users']}"
        )

        if stats['last_feedback_date']:
            last_date = stats['last_feedback_date'][:16].replace('T', ' ')
            stats_text += f"\n🕐 Последнее обращение: {last_date}"

        for admin_username in ADMIN_USERNAMES:
            try:
                chat_id = self.admin_chat_ids.get(admin_username)
                if chat_id:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=stats_text,
                        parse_mode="HTML"
                    )

            except Exception as e:
                print(f"❌ Ошибка отправки статистики админу @{admin_username}: {e}")


# Глобальный экземпляр уведомителя
admin_notifier = AdminNotifier()