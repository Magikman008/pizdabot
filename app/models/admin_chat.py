from datetime import datetime

from sqlalchemy.sql.schema import Column
from sqlalchemy.sql.sqltypes import Integer, BigInteger, String, DateTime

from app.models import Base


class AdminChat(Base):
    __tablename__ = "admin_chat_registry"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, index=True, unique=False)
    chat_id = Column(BigInteger, nullable=False, index=True)
    registered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
