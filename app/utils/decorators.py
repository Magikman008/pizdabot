from functools import wraps

from aiogram.types import Message

from app.controllers import subscription_manager
from app.utils.tools import is_admin, has_premium_access


def admin_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not is_admin(message):
            return
        return await handler(message, *args, **kwargs)

    return wrapper


def premium_only(handler):
    @wraps(handler)
    async def wrapper(message: Message, *args, **kwargs):
        if not has_premium_access(message.from_user.id):
            keyboard = subscription_manager.create_subscription_keyboard(message)
            await message.answer(
                "⭐ *Эта функция доступна только подписчикам\\!*\n\n"
                f"Купите премиум\\-подписку за {subscription_manager.SUBSCRIPTION_PRICE_STARS} ⭐",
                reply_markup=keyboard,
                parse_mode="MarkdownV2",
            )
            return
        return await handler(message, *args, **kwargs)

    return wrapper
