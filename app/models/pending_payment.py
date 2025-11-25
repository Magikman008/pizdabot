from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Numeric

from app.models import Base


class PendingPayment(Base):
    """Временное хранилище для платежей ЮКасса"""
    __tablename__ = "pending_payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    payment_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Для удобства поиска
    __table_args__ = (
        {'mysql_charset': 'utf8mb4'},
    )
