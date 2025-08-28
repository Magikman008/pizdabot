from datetime import datetime

from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.models import Base


class RoastWord(Base):
    __tablename__ = "roast_words"

    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String(255), nullable=False, unique=True)  # уникальное слово

    # связь к событиям
    events = relationship("RoastEvent", back_populates="word")


class RoastEvent(Base):
    __tablename__ = "roast_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    word_id = Column(Integer, ForeignKey("roast_words.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # связь к слову
    word = relationship("RoastWord", back_populates="events")
