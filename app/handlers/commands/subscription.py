from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    LabeledPrice,
    CallbackQuery,
    PreCheckoutQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.bot import bot
from app.controllers import subscription_manager
from app.db import SessionLocal
from app.logger import logger
from app.models import SubscriptionType, PendingPayment
from app.utils.tools import escape_markdown

# Импортируем сервис ЮКасса только если он доступен
try:
    from app.services.yookassa_service import yookassa_service

    YOOKASSA_AVAILABLE = True
except ImportError:
    logger.warning("ЮКасса не доступна - установите yookassa SDK")
    YOOKASSA_AVAILABLE = False

subscription_router = Router()


@subscription_router.message(Command("sub"))
async def show_subscription_info(message: Message):
    """Показать информацию о подписке"""
    description = subscription_manager.get_subscription_description()

    await message.answer(
        escape_markdown(description),
        reply_markup=subscription_manager.create_subscription_keyboard(message),
        parse_mode="MarkdownV2",
    )


@subscription_router.callback_query(F.data.startswith("buy_sub:"))
async def process_subscription_purchase(callback: CallbackQuery):
    """Обработка покупки подписки"""
    await callback.answer()

    try:
        # Формат: buy_sub:user_id:chat_id:type
        _, user_id_str, chat_id_str, type_name = callback.data.split(":")
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)

        # Получаем цену по типу
        price = subscription_manager.get_price_by_name(type_name)

        if not price:
            await callback.message.answer("❌ Неверный тип подписки")
            return

        # Telegram Stars
        if type_name == SubscriptionType.TELEGRAM_STARS.value:
            await bot.send_invoice(
                chat_id=callback.message.chat.id,
                title="⭐ Премиум-подписка Подъёбыш",
                description=f"Подписка на {subscription_manager.SUBSCRIPTION_DURATION_DAYS} дней",
                payload=f"sub:{user_id}:{chat_id}:{type_name}",
                provider_token="",
                currency="XTR",
                prices=[LabeledPrice(label="Премиум", amount=price)],
                need_name=False,
                need_phone_number=False,
                need_email=False,
                need_shipping_address=False,
            )

        # ЮКасса
        elif type_name == SubscriptionType.YOOKASSA.value:
            if not YOOKASSA_AVAILABLE:
                await callback.message.answer(
                    "❌ Оплата через ЮКассу временно недоступна"
                )
                return

            # Создаём платёж
            bot_username = (await bot.get_me()).username
            return_url = f"https://t.me/{bot_username}"

            success, payment_url, payment_id = yookassa_service.create_payment(
                amount=float(price),
                description=f"Подписка Подъёбыш на {subscription_manager.SUBSCRIPTION_DURATION_DAYS} дней",
                return_url=return_url,
                metadata={
                    "user_id": str(user_id),
                    "chat_id": str(chat_id),
                }
            )

            if not success or not payment_url:
                await callback.message.answer(
                    "❌ Ошибка создания платежа\\. Попробуйте позже\\.",
                    parse_mode="MarkdownV2"
                )
                return

            # Сохраняем платёж в БД
            with SessionLocal() as session:
                pending = PendingPayment(
                    payment_id=payment_id,
                    user_id=user_id,
                    chat_id=chat_id,
                    amount=float(price),
                )
                session.add(pending)
                session.commit()

            # Создаём короткий callback_data
            # Используем ID записи в БД вместо UUID
            with SessionLocal() as session:
                pending = session.query(PendingPayment).filter_by(
                    payment_id=payment_id
                ).first()
                pending_id = pending.id

            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="💳 Перейти к оплате",
                            url=payment_url
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="✅ Проверить оплату",
                            callback_data=f"check_pay:{pending_id}"
                        )
                    ]
                ]
            )

            await callback.message.answer(
                escape_markdown(
                    f"""💳 **Оплата через ЮКассу**

💰 Сумма: {price} ₽
⏱️ Подписка на {subscription_manager.SUBSCRIPTION_DURATION_DAYS} дней

1️⃣ Нажмите "Перейти к оплате"
2️⃣ Оплатите картой, ЮMoney или SberPay
3️⃣ Вернитесь и нажмите "Проверить оплату"

🔒 Безопасная оплата через ЮКасса"""
                ),
                reply_markup=keyboard,
                parse_mode="MarkdownV2"
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке покупки подписки: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка\\. Попробуйте позже\\.",
            parse_mode="MarkdownV2"
        )


@subscription_router.callback_query(F.data.startswith("check_pay:"))
async def check_yookassa_payment(callback: CallbackQuery):
    """Проверка статуса платежа ЮКасса"""
    await callback.answer("Проверяю статус...")

    try:
        _, pending_id_str = callback.data.split(":")
        pending_id = int(pending_id_str)

        # Получаем данные платежа из БД
        with SessionLocal() as session:
            pending = session.query(PendingPayment).filter_by(id=pending_id).first()

            if not pending:
                await callback.message.answer("❌ Платёж не найден")
                return

            payment_id = pending.payment_id
            user_id = pending.user_id
            chat_id = pending.chat_id

        # Проверяем статус
        is_paid, status = yookassa_service.check_payment_status(payment_id)

        if is_paid:
            # Получаем полную информацию
            payment_info = yookassa_service.get_payment_info(payment_id)

            if payment_info:
                # Активируем подписку
                success, msg = subscription_manager.activate_subscription(
                    user_id=user_id,
                    chat_id=chat_id,
                    price=payment_info['amount'],
                    transaction_id=payment_id,
                    type_name=SubscriptionType.YOOKASSA.value,
                    yookassa_payment_id=payment_id,
                )

                if success:
                    # Удаляем из pending
                    with SessionLocal() as session:
                        session.query(PendingPayment).filter_by(
                            id=pending_id
                        ).delete()
                        session.commit()

                    await callback.message.answer(
                        escape_markdown(msg),
                        parse_mode="MarkdownV2"
                    )
                else:
                    await callback.message.answer(
                        "❌ Ошибка активации\\. Обратитесь к администратору\\.",
                        parse_mode="MarkdownV2"
                    )
        elif status == "pending":
            await callback.message.answer(
                "⏳ Платёж обрабатывается\\.\n\nПодождите и нажмите кнопку снова\\.",
                parse_mode="MarkdownV2"
            )
        elif status == "waiting_for_capture":
            await callback.message.answer(
                "⏳ Ожидание подтверждения\\.\n\nПодождите и нажмите кнопку снова\\.",
                parse_mode="MarkdownV2"
            )
        else:
            await callback.message.answer(
                f"❌ Платёж не завершён \\(статус: {status}\\)\\.\n\nПопробуйте оплатить заново\\.",
                parse_mode="MarkdownV2"
            )

    except Exception as e:
        logger.error(f"Ошибка проверки платежа: {e}")
        await callback.message.answer(
            "❌ Ошибка проверки\\. Попробуйте позже\\.",
            parse_mode="MarkdownV2"
        )


@subscription_router.callback_query(F.data.startswith("sub_info:"))
async def show_subscription_status(callback: CallbackQuery):
    """Показать статус подписки"""
    await callback.answer()

    _, chat_id_str = callback.data.split(":")
    chat_id = int(chat_id_str)

    sub_info = subscription_manager.get_subscription_info(chat_id)
    await callback.message.answer(escape_markdown(sub_info), parse_mode="MarkdownV2")


@subscription_router.pre_checkout_query()
async def pre_checkout_query_handler(pre_checkout_query: PreCheckoutQuery):
    """Обработка pre-checkout для Telegram Stars"""
    if pre_checkout_query.invoice_payload.startswith("sub:"):
        await pre_checkout_query.answer(ok=True)
    else:
        await pre_checkout_query.answer(ok=False, error_message="Неверный тип")


@subscription_router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешного платежа Telegram Stars"""
    payment = message.successful_payment

    if not payment.invoice_payload.startswith("sub:"):
        return

    try:
        _, user_id_str, chat_id_str, type_name = payment.invoice_payload.split(":")
        user_id = int(user_id_str)
        chat_id = int(chat_id_str)

        success, msg = subscription_manager.activate_subscription(
            user_id=user_id,
            chat_id=chat_id,
            price=payment.total_amount,
            transaction_id=payment.telegram_payment_charge_id,
            type_name=SubscriptionType.YOOKASSA.value,
        )

        if success:
            await bot.send_message(
                chat_id, escape_markdown(msg), parse_mode="MarkdownV2"
            )
        else:
            await message.answer(
                "❌ Ошибка активации\\. Обратитесь к администратору\\.",
                parse_mode="MarkdownV2"
            )
    except Exception as e:
        logger.error(f"Ошибка обработки платежа Stars: {e}")
        await message.answer(
            "❌ Произошла ошибка\\.", parse_mode="MarkdownV2"
        )
