from datetime import datetime

from sqlalchemy import Column, BigInteger, Boolean, Integer, DateTime

from .base import Base


class ChatConfig(Base):
    __tablename__ = "chat_config"

    id = Column(BigInteger, primary_key=True, index=True)
    enabled = Column(Boolean, nullable=False, default=True)
    response_chance = Column(Integer, nullable=False, default=100)
    last_modified = Column(DateTime, nullable=False, default=datetime.now)
    modified_by = Column(BigInteger, nullable=False)
