from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, BigInteger
from sqlalchemy.sql import func
from app.models import Base


class ChatInfo(Base):
    __tablename__ = "chat_info"

    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(BigInteger, unique=True, index=True, nullable=False)
    chat_type = Column(String(20),
                       nullable=False)  # private, group, supergroup, channel
    chat_title = Column(String(255))
    chat_username = Column(String(255))
    chat_description = Column(Text)
    members_count = Column(String(50))  # Строка, т.к. может быть "Недоступно"

    # Информация о добавившем пользователе
    added_by_user_id = Column(BigInteger, nullable=False)
    added_by_username = Column(String(255))
    added_by_first_name = Column(String(255))
    added_by_last_name = Column(String(255))

    # Метаданные
    added_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    bot_status = Column(String(20))  # member, administrator, left, kicked
    is_active = Column(Boolean, default=True)

    def __repr__(self):
        return f"<ChatInfo(chat_id={self.chat_id}, title={self.chat_title})>"
