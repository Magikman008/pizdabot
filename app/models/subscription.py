import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Enum,
    Numeric,
    BigInteger,
)
from sqlalchemy.orm import relationship

from app.models import Base


class SubscriptionType(enum.Enum):
    YOOKASSA = "yookassa"
    TELEGRAM_STARS = "telegram_stars"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    tg_chat_id = Column(BigInteger, nullable=True)

    activated_at = Column(DateTime, default=datetime.now)
    expires_at = Column(DateTime, nullable=False)

    transactions = relationship("Transaction", back_populates="subscription")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False)
    who_bought_id = Column(BigInteger, nullable=True)

    transaction_id = Column(String(512), nullable=False)
    amount_stars = Column(Numeric(10, 2), nullable=False)
    timestamp = Column(DateTime, default=datetime.now)
    type = Column(Enum(SubscriptionType), nullable=False)

    subscription = relationship("Subscription", back_populates="transactions")
