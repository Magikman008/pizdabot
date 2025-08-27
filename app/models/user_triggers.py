from datetime import date

from sqlalchemy import Column, Integer, String, Date, BigInteger, UniqueConstraint

from app.models import Base


class CustomTrigger(Base):
    __tablename__ = "custom_triggers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger_word = Column(String, nullable=False)
    response = Column(String, nullable=False)
    chat_id = Column(BigInteger, nullable=False)
    author_id = Column(BigInteger, nullable=False)
    created = Column(Date, default=date.today(), nullable=False)
    uses = Column(Integer, default=0, nullable=False)

    __table_args__ = (
        UniqueConstraint('chat_id', 'trigger_word', name='uq_chat_trigger'),
    )
