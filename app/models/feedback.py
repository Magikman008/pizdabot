"""
Модель для системы обратной связи - полностью переписанная
Хранение обращений пользователей в базе данных
"""
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index
from app.models import Base

class Feedback(Base):
    """
    Модель для хранения обращений пользователей
    Совместима с существующей архитектурой проекта
    """
    __tablename__ = 'feedback'

    # Основные поля
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True, comment="Telegram user ID")
    username = Column(String(255), nullable=True, comment="Telegram username без @")
    first_name = Column(String(255), nullable=True, comment="Имя пользователя")
    last_name = Column(String(255), nullable=True, comment="Фамилия пользователя")

    # Содержимое обращения
    message = Column(Text, nullable=False, comment="Текст обращения")

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True, comment="Прочитано админом")

    # Составные индексы для оптимизации запросов
    __table_args__ = (
        Index('idx_feedback_user_created', 'user_id', 'created_at'),
        Index('idx_feedback_unread_created', 'is_read', 'created_at'),
    )

    def __repr__(self) -> str:
        """Строковое представление объекта"""
        username_part = f"@{self.username}" if self.username else f"User_{self.user_id}"
        return f"<Feedback #{self.id} from {username_part}>"

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для JSON-сериализации
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'message': self.message,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_read': self.is_read
        }

    @property
    def display_name(self) -> str:
        """
        Возвращает отображаемое имя пользователя для админов
        """
        if self.username:
            return f"@{self.username}"
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return f"User {self.user_id}"

    @property
    def short_message(self) -> str:
        """
        Возвращает сокращенную версию сообщения для превью
        """
        if len(self.message) <= 100:
            return self.message
        return self.message[:100] + "..."

    @property
    def formatted_date(self) -> str:
        """
        Возвращает отформатированную дату создания
        """
        if self.created_at:
            return self.created_at.strftime("%Y-%m-%d %H:%M")
        return "Неизвестно"

    def mark_as_read(self) -> None:
        """
        Отметить обращение как прочитанное
        """
        self.is_read = True

    def is_recent(self, hours: int = 24) -> bool:
        """
        Проверить, является ли обращение недавним

        Args:
            hours: Количество часов для проверки

        Returns:
            bool: True если обращение создано в указанный период
        """
        if not self.created_at:
            return False

        time_diff = datetime.utcnow() - self.created_at
        return time_diff.total_seconds() < hours * 3600