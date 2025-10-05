"""
Менеджер для управления информацией о чатах
"""
import logging
from datetime import datetime
from typing import Optional, List
from sqlalchemy.exc import IntegrityError

from app.models.chat_info import ChatInfo

logger = logging.getLogger(__name__)


class ChatInfoManager:

    def __init__(self, session_maker):
        self.session_maker = session_maker

    async def save_chat_info(self, chat_data: dict) -> Optional[ChatInfo]:
        """
        Сохранение или обновление информации о чате
        """
        try:
            with self.session_maker() as session:
                # Проверяем, есть ли уже запись о чате
                existing_chat = session.query(ChatInfo).filter(
                    ChatInfo.chat_id == chat_data['chat_id']
                ).first()

                if existing_chat:
                    # Обновляем существующую запись
                    for key, value in chat_data.items():
                        if hasattr(existing_chat, key):
                            setattr(existing_chat, key, value)
                    existing_chat.updated_at = datetime.now()
                    existing_chat.is_active = True

                    session.commit()
                    session.refresh(existing_chat)
                    logger.info(f"Обновлена информация о чате {chat_data['chat_id']}")
                    return existing_chat
                else:
                    # Создаем новую запись
                    chat_info = ChatInfo(**chat_data)
                    session.add(chat_info)
                    session.commit()
                    session.refresh(chat_info)
                    logger.info(
                        f"Сохранена информация о новом чате {chat_data['chat_id']}")
                    return chat_info

        except IntegrityError as e:
            logger.error(
                f"Ошибка целостности при сохранении чата {chat_data['chat_id']}: {e}")
            return None
        except Exception as e:
            logger.error(
                f"Ошибка при сохранении информации о чате {chat_data['chat_id']}: {e}")
            return None

    async def update_chat_status(self, chat_id: int, is_active: bool) -> bool:
        """
        Обновление статуса активности чата
        """
        try:
            with self.session_maker() as session:
                chat_info = session.query(ChatInfo).filter(
                    ChatInfo.chat_id == chat_id
                ).first()

                if chat_info:
                    chat_info.is_active = is_active
                    chat_info.updated_at = datetime.now()
                    if not is_active:
                        chat_info.bot_status = "left"

                    session.commit()
                    logger.info(
                        f"Обновлен статус чата {chat_id}: активен = {is_active}")
                    return True
                else:
                    logger.warning(f"Чат {chat_id} не найден для обновления статуса")
                    return False

        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса чата {chat_id}: {e}")
            return False

    async def get_active_chats(self) -> List[ChatInfo]:
        """
        Получение списка активных чатов
        """
        try:
            with self.session_maker() as session:
                chats = session.query(ChatInfo).filter(
                    ChatInfo.is_active == True
                ).all()
                return chats
        except Exception as e:
            logger.error(f"Ошибка при получении активных чатов: {e}")
            return []

    async def get_chat_info(self, chat_id: int) -> Optional[ChatInfo]:
        """
        Получение информации о конкретном чате
        """
        try:
            with self.session_maker() as session:
                chat_info = session.query(ChatInfo).filter(
                    ChatInfo.chat_id == chat_id
                ).first()
                return chat_info
        except Exception as e:
            logger.error(f"Ошибка при получении информации о чате {chat_id}: {e}")
            return None
