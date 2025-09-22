from aiogram.types import Message

import app
from app.controllers import SubscriptionManager
from app.db import SessionLocal
from settings import ADMIN_USERNAMES


def escape_markdown(text: str) -> str:
    """
    Экранирование для MarkdownV2: экранирует все символы,
    которые Telegram считает специальными в MarkdownV2.
    """
    # Список всех спецсимволов MarkdownV2
    special_chars = r"+#\[]()~<>-=|{}!"
    # Экранируем каждый спецсимвол обратным слешем
    return "".join(f"\\{ch}" if ch in special_chars else ch for ch in text)


def is_admin(message: Message) -> bool:
    """Проверка, является ли пользователь администратором"""
    return message.from_user.username in ADMIN_USERNAMES


def has_premium_access(user_id: int) -> bool:
    """Проверка наличия премиум-доступа у пользователя"""
    subscription_manager = app.controllers.SubscriptionManager(SessionLocal)
    return subscription_manager.has_active_subscription(user_id)
