from functools import wraps

from aiogram.types import Message

from app.subscription_manager import subscription_manager
from app.utils.tools import is_admin, has_premium_access


def admin_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_admin(message):
            await message.answer(
                "❌ Эта команда доступна только администраторам!",
                parse_mode="MarkdownV2",
            )
            return
        return await handler(message, *args, **kwargs)

    return wrapper


def premium_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not has_premium_access(message.from_user.id):
            keyboard = subscription_manager.create_subscription_keyboard()
            await message.answer(
                "⭐ *Добавление триггеров доступно только подписчикам\\!*\n\n"
                f"Купите премиум\\-подписку за {subscription_manager.SUBSCRIPTION_PRICE_STARS} ⭐ чтобы добавлять свои триггеры:",
                reply_markup=keyboard,
                parse_mode="MarkdownV2",
            )
            return
        return await handler(message, *args, **kwargs)

    return wrapper
