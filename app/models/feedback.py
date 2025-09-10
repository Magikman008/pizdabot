"""
Модель для обратной связи пользователей
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Feedback(Base):
    """Модель для хранения обратной связи от пользователей"""
    __tablename__ = 'feedback'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    is_read = Column(Boolean, default=False, index=True)

    def __repr__(self):
        return f"<Feedback(id={self.id}, user_id={self.user_id}, created_at={self.created_at})>"

    def to_dict(self):
        """Преобразование в словарь для JSON"""
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
    def display_name(self):
        """Возвращает отображаемое имя пользователя"""
        if self.username:
            return f"@{self.username}"
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return f"User {self.user_id}"
