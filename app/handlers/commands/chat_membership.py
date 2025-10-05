"""
Обработчик событий добавления/удаления бота в чаты
"""
import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import ChatMemberUpdated
from aiogram.exceptions import TelegramBadRequest

from app.bot import bot
from app.controllers import chat_info_manager

chat_membership_router = Router()
logger = logging.getLogger(__name__)

@chat_membership_router.my_chat_member(
    F.new_chat_member.status.in_(["member", "administrator"])
)
async def bot_added_to_chat(event: ChatMemberUpdated):
    """
    Обработчик добавления бота в чат
    """
    chat = event.chat
    added_by_user = event.from_user

    try:
        # Получаем полную информацию о чате
        chat_info = await bot.get_chat(chat.id)

        # Получаем количество участников
        members_count = None
        if chat.type in ["group", "supergroup"]:
            try:
                members_count = await bot.get_chat_member_count(chat.id)
            except (TelegramBadRequest) as e:
                logger.warning(f"Не удалось получить количество участников для чата {chat.id}: {e}")
                members_count = "Недоступно"

        # Собираем информацию
        chat_data = {
            "chat_id": chat.id,
            "chat_type": chat.type,
            "chat_title": getattr(chat_info, 'title', 'Приватный чат'),
            "chat_username": getattr(chat_info, 'username', None),
            "chat_description": getattr(chat_info, 'description', None),
            "members_count": str(members_count) if members_count else None,
            "added_by_user_id": added_by_user.id,
            "added_by_username": added_by_user.username,
            "added_by_first_name": added_by_user.first_name,
            "added_by_last_name": getattr(added_by_user, 'last_name', None),
            "added_at": datetime.now(),
            "bot_status": event.new_chat_member.status,
            "is_active": True
        }

        # Сохраняем информацию
        await chat_info_manager.save_chat_info(chat_data)

        # Инициализируем настройки чата
        # settings_manager = ChatSettingsManager()
        # await settings_manager.get_or_create_settings(chat.id)

        # Отправляем приветствие
        welcome_message = await create_welcome_message(chat_data)
        if welcome_message and chat.type != "private":
            await bot.send_message(chat.id, welcome_message)

        logger.info(f"Бот добавлен в чат {chat.id} ({chat_data['chat_title']}) пользователем {added_by_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке добавления в чат {chat.id}: {e}")

@chat_membership_router.my_chat_member(
    F.new_chat_member.status.in_(["left", "kicked"])
)
async def bot_removed_from_chat(event: ChatMemberUpdated):
    """
    Обработчик удаления бота из чата
    """
    chat = event.chat
    removed_by_user = event.from_user

    try:
        await chat_info_manager.update_chat_status(chat.id, False)

        logger.info(f"Бот удален из чата {chat.id} пользователем {removed_by_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке удаления из чата {chat.id}: {e}")

async def create_welcome_message(chat_data: dict) -> str:
    """
    Создание приветственного сообщения
    """
    if chat_data['chat_type'] == "private":
        return None

    return f"""👋 Привет! Я...\n
    да похуй в целом.\n 
    Продолжай пиздеть в чате, а если что-то непонятно -- используй /help.
"""
