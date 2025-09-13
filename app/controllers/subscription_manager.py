"""
Модуль для управления подписками через Telegram Stars
Позволяет пользователям покупать подписки за звёздочки Telegram
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple

from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.orm import Session

from app.models import Subscription, Transaction, SubscriptionType


class SubscriptionManager:
    # Настройки подписки
    SUBSCRIPTION_PRICE_STARS = 1  # Цена подписки в звёздочках
    SUBSCRIPTION_PRICE_RUBS = 150  # Цена подписки в рублях
    SUBSCRIPTION_DURATION_DAYS = 30  # Длительность подписки в днях

    def __init__(self, session_maker):
        """
        Менеджер подписок через SQLAlchemy

        Args:
            session (Session): SQLAlchemy сессия
        """
        self.session_maker = session_maker

    def has_active_subscription(self, tg_chat_id: int) -> bool:
        """Есть ли активная подписка у пользователя/чата"""
        with self.session_maker() as session:
            sub = (
                session.query(Subscription)
                .filter_by(tg_chat_id=tg_chat_id)
                .order_by(Subscription.expires_at.desc())
                .first()
            )
        if not sub:
            return False
        return sub.expires_at > datetime.now()

    def get_subscription_info(self, tg_chat_id: int = None) -> str:
        """Текстовая информация о подписке"""
        if not self.has_active_subscription(tg_chat_id):
            return f"""⭐ **Информация о подписке:**

❌ Подписка неактивна
💰 Цена: {self.SUBSCRIPTION_PRICE_STARS} звёздочка
⏱️ Длительность: {self.SUBSCRIPTION_DURATION_DAYS} дней

💡 Используйте /sub для покупки подписки!"""
        with self.session_maker() as session:
            sub = (
                session.query(Subscription)
                .filter_by(tg_chat_id=tg_chat_id)
                .order_by(Subscription.expires_at.desc())
                .first()
            )

        days_left = (sub.expires_at - datetime.now()).days

        return f"""⭐ **Информация о подписке:**

✅ Подписка активна
📅 Истекает: {sub.expires_at.strftime('%d.%m.%Y %H:%M')}
⏰ Осталось дней: {days_left}"""

    def activate_subscription(
        self, user_id: int, chat_id: int, price: int, transaction_id: str = None, type_name: str = None
    ) -> Tuple[bool, str]:
        """Активировать или продлить подписку"""
        now = datetime.now()

        with self.session_maker() as session:
            sub = (
                session.query(Subscription)
                .filter_by(tg_chat_id=chat_id)
                .order_by(Subscription.expires_at.desc())
                .first()
            )

            if sub and sub.expires_at > now:
                new_expiry = sub.expires_at + timedelta(
                    days=self.SUBSCRIPTION_DURATION_DAYS
                )
                sub.expires_at = new_expiry
            else:
                new_expiry = now + timedelta(days=self.SUBSCRIPTION_DURATION_DAYS)
                sub = Subscription(
                    tg_chat_id=chat_id,
                    activated_at=now,
                    expires_at=new_expiry,
                )
                session.add(sub)

            # сохраняем транзакцию
            if transaction_id:
                txn = Transaction(
                    subscription=sub,
                    transaction_id=transaction_id,
                    amount_stars=price,
                    timestamp=now,
                    who_bought_id=user_id,
                    type=SubscriptionType.TELEGRAM_STARS if type_name == "telegram_stars" else SubscriptionType.YOOKASSA,
                )
                session.add(txn)

            session.commit()

        return (
            True,
            f"""✅ **Подписка активирована!**

📅 Действует до: {new_expiry.strftime('%d.%m.%Y %H:%M')}

🚀 Теперь вам доступны все премиум-функции бота!""",
        )

    def get_subscription_description(self) -> str:
        """
        Получить описание подписки

        Returns:
            str: Описание подписки
        """
        return f"""⭐ **Премиум-подписка Подъёбыш**

💰 **Цена:** {self.SUBSCRIPTION_PRICE_STARS} звёздочка Telegram
⏱️ **Длительность:** {self.SUBSCRIPTION_DURATION_DAYS} дней

🎯 **Что включено:**
• Возможность добавлять пользовательские триггеры

💡 Звёздочки можно купить в настройках Telegram или получить от других пользователей."""

    def get_premium_features_list(self) -> list:
        """
        Получить список премиум-функций

        Returns:
            list: Список премиум-функций
        """
        return [
            "Добавление пользовательских триггеров",
            "Увеличенные лимиты на триггеры",
            "Приоритетная обработка",
            "Расширенная статистика",
            "Эксклюзивные команды",
            "Техническая поддержка",
        ]

    def get_all_subscribers(self) -> Dict[int, Subscription]:
        """Вернуть всех активных подписчиков"""
        now = datetime.now()
        with self.session_maker() as session:
            subs = (
                session.query(Subscription).filter(Subscription.expires_at > now).all()
            )
        return {sub.tg_chat_id: sub for sub in subs}

    def create_subscription_keyboard(self, message: Message) -> InlineKeyboardMarkup:
        buy_button_stars = InlineKeyboardButton(
            text=f"⭐ Купить подписку за {SubscriptionManager.SUBSCRIPTION_PRICE_STARS} звёздочку",
            callback_data=f"buy_subscription:{message.from_user.id}:{message.chat.id}:{SubscriptionManager.SUBSCRIPTION_PRICE_STARS}:TELEGRAM_STARS",
        )
        buy_button_rubs = InlineKeyboardButton(
            text=f"⭐ Купить подписку за {SubscriptionManager.SUBSCRIPTION_PRICE_RUBS} рублей",
            callback_data=f"buy_subscription:{message.from_user.id}:{message.chat.id}:{SubscriptionManager.SUBSCRIPTION_PRICE_RUBS}:YOOKASSA",
        )

        # Кнопка информации
        info_button = InlineKeyboardButton(
            text="ℹ️ Информация о подписке",
            callback_data=f"subscription_info:{message.chat.id}",
        )

        return InlineKeyboardMarkup(
            inline_keyboard=[[buy_button_rubs], [buy_button_stars], [info_button]]
        )
