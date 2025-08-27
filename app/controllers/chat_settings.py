"""
Модуль для управления настройками чата
Позволяет отключать/включать бота и настраивать вероятность ответов
"""

import random
from datetime import datetime

from app.models import ChatConfig


class ChatSettingsManager:
    def __init__(self, db_session_factory):
        """
        Инициализация менеджера настроек чата

        Args:
            db_session_factory: sessionmaker из db.py
        """
        self.db_session_factory = db_session_factory

    def _get_or_create_chat(
        self, chat_id: int
    ) -> ChatConfig:
        """Получить или создать настройки для чата"""
        with self.db_session_factory() as session:
            chat = session.query(ChatConfig).filter_by(id=chat_id).first()
            if not chat:
                chat = ChatConfig(
                    id=chat_id,
                    enabled=True,
                    response_chance=100,
                )
                session.add(chat)
                session.commit()
                session.refresh(chat)
            return chat

    def set_bot_enabled(self, chat_id: int, enabled: bool, user_id: int):
        """Включить/выключить бота в чате"""
        with self.db_session_factory() as session:
            chat = self._get_or_create_chat(chat_id)
            chat.enabled = enabled
            chat.last_modified = datetime.now()
            chat.modified_by = user_id
            session.add(chat)
            session.commit()

        status = "включен" if enabled else "выключен"
        emoji = "✅" if enabled else "❌"
        return True, f"{emoji} Бот {status} в этом чате!"

    def set_response_chance(self, chat_id: int, chance: int, user_id: int):
        """Установить вероятность ответа"""
        if not (0 <= chance <= 100):
            return False, "❌ Вероятность должна быть от 0 до 100!"

        with self.db_session_factory() as session:
            chat = self._get_or_create_chat(chat_id)
            chat.response_chance = chance
            chat.last_modified = datetime.now()
            chat.modified_by = user_id
            session.add(chat)
            session.commit()

        return True, f"🎯 Вероятность ответа установлена: {chance}%"

    def should_respond(self, chat_id: int) -> bool:
        """Определить, должен ли бот отвечать"""
        chat = self._get_or_create_chat(chat_id)

        if not chat.enabled:
            return False
        if chat.response_chance == 0:
            return False
        if chat.response_chance == 100:
            return True
        return random.randint(1, 100) <= chat.response_chance

    def get_chat_info(self, chat_id: int) -> str:
        """Получить информацию о чате"""
        chat = self._get_or_create_chat(chat_id)

        status_emoji = "✅" if chat.enabled else "❌"
        status_text = "включен" if chat.enabled else "выключен"
        last_modified = chat.last_modified.strftime("%d.%m.%Y %H:%M")

        return f"""⚙️ **Настройки бота в чате:**

{status_emoji} Статус: {status_text}
🎯 Вероятность ответа: {chat.response_chance}%
📅 Последнее изменение: {last_modified}"""

    def reset_chat_settings(self, chat_id: int, user_id: int):
        """Сбросить настройки к значениям по умолчанию"""
        with self.db_session_factory() as session:
            chat = self._get_or_create_chat(chat_id)
            chat.enabled = True
            chat.response_chance = 100
            chat.last_modified = datetime.now()
            chat.modified_by = user_id
            session.add(chat)
            session.commit()

        return True, "🔄 Настройки чата сброшены к значениям по умолчанию!"
