from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    BigInteger,
    JSON,
)
from sqlalchemy.sql import func
from app.models import Base


class ChatInfoHistory(Base):
    __tablename__ = "chat_info_history"

    id = Column(Integer, primary_key=True, index=True)
    snapshot_date = Column(DateTime(timezone=True), server_default=func.now())
    chat_id = Column(BigInteger, index=True, nullable=False)
    chat_type = Column(String(20), nullable=False)
    chat_title = Column(String(255))
    chat_username = Column(String(255))
    chat_description = Column(Text)
    members_count = Column(String(50))
    bot_status = Column(String(20))
    is_active = Column(Boolean, default=True)
