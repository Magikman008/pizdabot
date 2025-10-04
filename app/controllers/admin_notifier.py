import asyncio
from datetime import datetime
from typing import Optional

from app.bot import bot
from app.models.admin_chat import AdminChat
from app.utils.tools import escape_markdown


class AdminNotifier:
    def __init__(self, session_maker):
        self.session_maker = session_maker

    def register_admin(self, username: str, chat_id: int) -> bool:
        """
        Сохраняет или обновляет запись администратора для получения уведомлений.
        """
        session = self.session_maker()
        try:
            # Проверяем наличие записи
            record: Optional[AdminChat] = (
                session.query(AdminChat)
                .filter(AdminChat.username == username, AdminChat.chat_id == chat_id)
                .first()
            )
            if record:
                # Обновляем время регистрации
                record.registered_at = datetime.utcnow()
            else:
                record = AdminChat(username=username, chat_id=chat_id)
                session.add(record)
            session.commit()
            print(f"✅ AdminNotifier: зарегистрирован @{username} (chat_id={chat_id})")
            return True
        except Exception as e:
            session.rollback()
            print(f"❌ AdminNotifier: ошибка регистрации @{username}: {e}")
            return False
        finally:
            session.close()

    def get_admin_chats(self) -> list[type[AdminChat]]:
        """
        Возвращает все записи администраторов для рассылки уведомлений.
        """
        session = self.session_maker()
        try:
            return session.query(AdminChat).all()
        finally:
            session.close()

    async def notify_all(self, text: str):
        """
        Асинхронная рассылка текста всем зарегистрированным администраторам.
        """
        admins = self.get_admin_chats()
        tasks = []
        for admin in admins:
            tasks.append(
                bot.send_message(
                    chat_id=admin.chat_id,
                    text=escape_markdown(text),
                    parse_mode="MarkdownV2",
                )
            )
        results = await asyncio.gather(*tasks, return_exceptions=True)
        success = sum(1 for r in results if not isinstance(r, Exception))
        print(f"📊 Рассылка уведомлений завершена: {success}/{len(admins)}")
        return success
