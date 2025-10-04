"""
Модель для системы обратной связи - полностью переписанная
Хранение обращений пользователей в базе данных
"""

from datetime import datetime
from typing import Dict, Any

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index

from app.models import Base


class Feedback(Base):
    """
    Модель для хранения обращений пользователей
    Совместима с существующей архитектурой проекта
    """

    __tablename__ = "feedback"

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
    is_read = Column(
        Boolean, default=False, nullable=False, index=True, comment="Прочитано админом"
    )

    def to_dict(self) -> Dict[str, Any]:
        """
        Преобразование объекта в словарь для JSON-сериализации
        """
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "message": self.message,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_read": self.is_read,
        }

    def mark_as_read(self) -> None:
        """
        Отметить обращение как прочитанное
        """
        self.is_read = True
