from aiogram.types import Message

from settings import ADMIN_USERNAMES


def escape_markdown(text: str) -> str:
    """
    Экранирование для MarkdownV2: экранирует все символы,
    которые Telegram считает специальными в MarkdownV2.
    """
    # Список всех спецсимволов MarkdownV2
    special_chars = r"+#\[]().~<>-=_|{}!"
    # Экранируем каждый спецсимвол обратным слешем
    return "".join(f"\\{ch}" if ch in special_chars else ch for ch in text)


def is_admin(message: Message) -> bool:
    """Проверка, является ли пользователь администратором"""
    return message.from_user.username in ADMIN_USERNAMES


def has_premium_access(user_id: int) -> bool:
    """Проверка наличия премиум-доступа у пользователя"""
    from app.controllers import subscription_manager

    return subscription_manager.has_active_subscription(user_id)

def split_long_message(text: str, max_length: int = 4000) -> list:
    """Разбить длинное сообщение на части"""
    if len(text) <= max_length:
        return [text]

    messages = []
    lines = text.split('\n')
    current_message = ""

    for line in lines:
        if len(current_message + line + '\n') <= max_length:
            current_message += line + '\n'
        else:
            if current_message:
                messages.append(current_message.rstrip())
                current_message = line + '\n'
            else:
                # Если одна строка больше лимита, принудительно обрезаем
                messages.append(line[:max_length])
                current_message = line[max_length:] + '\n'

    if current_message:
        messages.append(current_message.rstrip())

    return messages
