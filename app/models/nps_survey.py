"""
Модель для системы NPS (Net Promoter Score) опросов
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, BigInteger, Text, \
    UniqueConstraint
from app.models import Base


class NPSSurvey(Base):
    """
    Модель для хранения NPS оценок пользователей
    """
    __tablename__ = "nps_surveys"

    # Основные поля
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True, comment="Telegram user ID")
    chat_id = Column(BigInteger, nullable=False, index=True, comment="Telegram chat ID")
    username = Column(String(255), nullable=True, comment="Telegram username без @")

    # NPS данные
    score = Column(Integer, nullable=False, comment="Оценка от 0 до 10")
    trigger_count = Column(Integer, nullable=False,
                           comment="Количество триггеров до опроса")
    survey_message_id = Column(BigInteger, nullable=True,
                               comment="ID сообщения с опросом")

    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Уникальный индекс: один пользователь не может отвечать дважды в один день в одном чате
    __table_args__ = (
        UniqueConstraint('user_id', 'chat_id', 'created_at',
                         name='unique_user_daily_response'),
    )

    @property
    def nps_category(self) -> str:
        """Определяет категорию NPS"""
        if self.score >= 9:
            return "promoter"
        elif self.score >= 7:
            return "passive"
        else:
            return "detractor"
