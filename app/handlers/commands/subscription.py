from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    LabeledPrice,
    CallbackQuery,
    PreCheckoutQuery,
)

import settings
from app.bot import bot
from app.controllers import subscription_manager
from app.logger import logger
from app.models import SubscriptionType
from app.utils.decorators import premium_only
from app.utils.tools import escape_markdown
from settings import ADMIN_USERNAMES

subscription_router = Router()


@subscription_router.message(Command("sub"))
async def show_subscription_info(message: Message):
    """Показать информацию о подписке и возможность покупки"""
    description = subscription_manager.get_subscription_description()

    await message.answer(
        escape_markdown(description),
        reply_markup=subscription_manager.create_subscription_keyboard(message),
        parse_mode="MarkdownV2",
    )


@subscription_router.callback_query(F.data.startswith("buy_subscription:"))
async def process_subscription_purchase(callback: CallbackQuery):
    """Обработка покупки подписки за звёздочки"""
    await callback.answer()

    try:
        _, user_id_str, chat_id_str, price, type_name = callback.data.split(":")
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)
        price = int(price)

        # Создаем инвойс для оплаты звёздочками
        prices = [LabeledPrice(label="Премиум подписка", amount=price * 100)]

        match type_name:
            case SubscriptionType.TELEGRAM_STARS.value:
                await bot.send_invoice(
                    chat_id=callback.message.chat.id,
                    title="⭐ Премиум-подписка Подъёбыш",
                    description=f"Подписка на {subscription_manager.SUBSCRIPTION_DURATION_DAYS} дней с премиум-функциями",
                    payload=f"subscription:{user_id}:{chat_id}:{type_name}",
                    provider_token="",  # Для звёздочек пусто
                    currency="XTR",
                    prices=[LabeledPrice(label="Премиум подписка", amount=price)],
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    need_shipping_address=False,
                    send_phone_number_to_provider=False,
                    send_email_to_provider=False,
                    is_flexible=False,
                )
            case SubscriptionType.YOOKASSA.value:
                await bot.send_invoice(
                    chat_id=callback.message.chat.id,
                    title="⭐ Премиум-подписка Подъёбыш",
                    description=f"Подписка на {subscription_manager.SUBSCRIPTION_DURATION_DAYS} дней с премиум-функциями",
                    payload=f"subscription:{user_id}:{chat_id}:{type_name}",
                    provider_token=settings.yookassa_token,
                    currency="RUB",
                    prices=[LabeledPrice(label="Премиум подписка", amount=price * 100)],
                    need_name=False,
                    need_phone_number=False,
                    need_email=False,
                    need_shipping_address=False,
                    send_phone_number_to_provider=False,
                    send_email_to_provider=False,
                    is_flexible=False,
                )
    except Exception as e:
        logger.error(f"Ошибка при создании инвойса: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при создании платежа\\. Попробуйте позже\\.",
            parse_mode="MarkdownV2",
        )


@subscription_router.callback_query(F.data.startswith("subscription_info"))
async def show_subscription_status(callback: CallbackQuery):
    """Показать статус подписки пользователя"""
    await callback.answer()

    _, chat_id_str = callback.data.split(":")
    chat_id = int(chat_id_str)

    sub_info = subscription_manager.get_subscription_info(chat_id)
    await callback.message.answer(escape_markdown(sub_info), parse_mode="MarkdownV2")


@subscription_router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre-checkout запроса"""
    # Проверяем payload
    if pre_checkout_query.invoice_payload.startswith("subscription:"):
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(ok=False, error_message="Неверный тип платежа")


@subscription_router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешного платежа"""
    payment = message.successful_payment

    # Проверяем, что это платеж за подписку
    if not payment.invoice_payload.startswith("subscription:"):
        return

    try:
        _, user_id_str, chat_id_str, type_name = payment.invoice_payload.split(":")
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)

        # Активируем подписку
        success, msg = subscription_manager.activate_subscription(
            user_id=user_id,
            chat_id=chat_id,
            price=payment.total_amount / 100,
            transaction_id=payment.telegram_payment_charge_id,
            type_name=type_name,
        )

        if success:
            await bot.send_message(
                chat_id, escape_markdown(msg), parse_mode="MarkdownV2"
            )
        else:
            await message.answer(
                "❌ Ошибка при активации подписки\\. Обратитесь к администратору\\.",
                parse_mode="MarkdownV2",
            )
    except Exception as e:
        logger.error(f"Ошибка при обработке платежа: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке платежа\\.", parse_mode="MarkdownV2"
        )
