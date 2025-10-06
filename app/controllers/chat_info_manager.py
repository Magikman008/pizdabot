"""
Менеджер для управления информацией о чатах
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict
from sqlalchemy.exc import IntegrityError
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.bot import bot
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
                existing_chat = (
                    session.query(ChatInfo)
                    .filter(ChatInfo.chat_id == chat_data["chat_id"])
                    .first()
                )

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
                        f"Сохранена информация о новом чате {chat_data['chat_id']}"
                    )
                    return chat_info

        except IntegrityError as e:
            logger.error(
                f"Ошибка целостности при сохранении чата {chat_data['chat_id']}: {e}"
            )
            return None
        except Exception as e:
            logger.error(
                f"Ошибка при сохранении информации о чате {chat_data['chat_id']}: {e}"
            )
            return None

    async def update_chat_status(self, chat_id: int, is_active: bool) -> bool:
        """
        Обновление статуса активности чата
        """
        try:
            with self.session_maker() as session:
                chat_info = (
                    session.query(ChatInfo).filter(ChatInfo.chat_id == chat_id).first()
                )

                if chat_info:
                    chat_info.is_active = is_active
                    chat_info.updated_at = datetime.now()
                    if not is_active:
                        chat_info.bot_status = "left"

                    session.commit()
                    logger.info(
                        f"Обновлен статус чата {chat_id}: активен = {is_active}"
                    )
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
                chats = session.query(ChatInfo).filter(ChatInfo.is_active == True).all()
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
                chat_info = (
                    session.query(ChatInfo).filter(ChatInfo.chat_id == chat_id).first()
                )
                return chat_info
        except Exception as e:
            logger.error(f"Ошибка при получении информации о чате {chat_id}: {e}")
            return None

    async def update_all_chats_info(self) -> Dict[str, int]:
        """
        Обновляет информацию о всех активных чатах.

        Returns:
            Статистика обновления: updated, errors, total, deactivated
        """

        stats = {"updated": 0, "errors": 0, "total": 0, "deactivated": 0}

        try:
            # Получаем список всех активных чатов
            active_chats = await self.get_active_chats()
            stats["total"] = len(active_chats)

            logger.info(f"Начинаем обновление информации для {stats['total']} чатов")

            for chat_info in active_chats:
                try:
                    # Получаем свежую информацию о чате через Telegram API
                    chat_data = await bot.get_chat(chat_info.chat_id)

                    # Получаем количество участников для групп
                    members_count = None
                    if chat_data.type in ["group", "supergroup"]:
                        try:
                            members_count = await bot.get_chat_member_count(
                                chat_info.chat_id
                            )
                        except (TelegramBadRequest, TelegramForbiddenError) as e:
                            logger.warning(
                                f"Не удалось получить количество участников для чата {chat_info.chat_id}: {e}"
                            )
                            members_count = "Недоступно"

                    # Получаем статус бота в чате
                    try:
                        bot_member = await bot.get_chat_member(
                            chat_info.chat_id, bot.id
                        )
                        bot_status = bot_member.status
                        is_active = bot_status in ["member", "administrator"]
                    except (TelegramBadRequest, TelegramForbiddenError) as e:
                        logger.warning(f"Бот удален из чата {chat_info.chat_id}: {e}")
                        bot_status = "left"
                        is_active = False

                    # Формируем обновленные данные
                    updated_data = {
                        "chat_id": chat_info.chat_id,
                        "chat_type": chat_data.type,
                        "chat_title": getattr(chat_data, "title", "Приватный чат"),
                        "chat_username": getattr(chat_data, "username", None),
                        "chat_description": getattr(chat_data, "description", None),
                        "members_count": str(members_count) if members_count else None,
                        # Сохраняем оригинальную информацию о том, кто добавил бота
                        "added_by_user_id": chat_info.added_by_user_id,
                        "added_by_username": chat_info.added_by_username,
                        "added_by_first_name": chat_info.added_by_first_name,
                        "added_by_last_name": chat_info.added_by_last_name,
                        "added_at": chat_info.added_at,  # Не изменяем дату добавления
                        "updated_at": datetime.now(),
                        "bot_status": bot_status,
                        "is_active": is_active,
                    }

                    # Сохраняем обновленную информацию
                    updated_chat = await self.save_chat_info(updated_data)

                    if updated_chat:
                        if is_active:
                            stats["updated"] += 1
                            logger.debug(f"Обновлен активный чат {chat_info.chat_id}")
                        else:
                            stats["deactivated"] += 1
                            logger.info(
                                f"Чат {chat_info.chat_id} помечен как неактивный"
                            )
                    else:
                        stats["errors"] += 1
                        logger.error(
                            f"Не удалось сохранить данные для чата {chat_info.chat_id}"
                        )

                except (TelegramBadRequest, TelegramForbiddenError) as e:
                    # Бот удален из чата или нет доступа
                    logger.info(f"Бот удален из чата {chat_info.chat_id}: {e}")
                    await self.update_chat_status(chat_info.chat_id, False)
                    stats["deactivated"] += 1

                except Exception as e:
                    logger.error(f"Ошибка обновления чата {chat_info.chat_id}: {e}")
                    stats["errors"] += 1

            logger.info(
                f"Обновление завершено: обновлено {stats['updated']}, деактивировано {stats['deactivated']}, ошибок {stats['errors']}"
            )
            return stats

        except Exception as e:
            logger.error(f"Критическая ошибка при обновлении чатов: {e}")
            return stats
