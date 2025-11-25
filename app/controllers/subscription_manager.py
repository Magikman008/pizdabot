"""
Модуль для управления подписками через Telegram Stars и ЮКассу
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import settings
from app.models import SubscriptionType
from app.models.subscription import Subscription, Transaction


class SubscriptionManager:
    # Настройки подписки из конфига
    SUBSCRIPTION_PRICE_STARS = getattr(settings, 'SUBSCRIPTION_PRICE_STARS', 1)
    SUBSCRIPTION_PRICE_RUBS = getattr(settings, 'SUBSCRIPTION_PRICE_RUBLES', 150)
    SUBSCRIPTION_DURATION_DAYS = getattr(settings, 'SUBSCRIPTION_DURATION_DAYS', 30)

    def __init__(self, session_maker):
        self.session_maker = session_maker

    @classmethod
    def get_types_dict(cls) -> dict:
        """Получить словарь доступных типов подписок с ценами"""
        return {
            SubscriptionType.YOOKASSA: cls.SUBSCRIPTION_PRICE_RUBS,
            SubscriptionType.TELEGRAM_STARS: cls.SUBSCRIPTION_PRICE_STARS,
        }

    @classmethod
    def get_price_by_name(cls, name):
        """Получить цену по типу подписки"""
        return cls.get_types_dict().get(SubscriptionType(name))

    def has_active_subscription(self, tg_chat_id: int) -> bool:
        """Есть ли активная подписка у пользователя/чата"""
        with self.session_maker() as session:
            chat_sub = (
                session.query(Subscription)
                .filter_by(tg_chat_id=tg_chat_id)
                .order_by(Subscription.expires_at.desc())
                .first()
            )
        if not chat_sub:
            return False
        return chat_sub.expires_at > datetime.now()

    def get_subscription_info(self, tg_chat_id: int = None) -> str:
        """Текстовая информация о подписке"""
        if not self.has_active_subscription(tg_chat_id):
            return f"""⭐ **Информация о подписке:**

❌ Подписка неактивна
💰 Цена: {self.SUBSCRIPTION_PRICE_STARS} звёздочка или {self.SUBSCRIPTION_PRICE_RUBS} ₽
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
            self,
            user_id: int,
            chat_id: int,
            price: float,
            transaction_id: str = None,
            type_name: str = None,  # Это строка, например "yookassa"
            yookassa_payment_id: str = None,
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

            # Сохраняем транзакцию
            if transaction_id:
                # ✅ ИСПРАВЛЕНИЕ: преобразуем строку в enum
                subscription_type = SubscriptionType(type_name) if type_name else None

                txn = Transaction(
                    subscription=sub,
                    transaction_id=transaction_id,
                    amount_stars=price,
                    timestamp=now,
                    who_bought_id=user_id,
                    type=subscription_type,  # ✅ Передаём enum, а не строку
                    yookassa_payment_id=yookassa_payment_id,
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
        """Получить описание подписки"""
        return f"""⭐ **Премиум-подписка Подъёбыш**

💰 **Цена:** 
• {self.SUBSCRIPTION_PRICE_STARS} звёздочка Telegram
• {self.SUBSCRIPTION_PRICE_RUBS} рублей (банковская карта, ЮMoney, SberPay)

⏱️ **Длительность:** {self.SUBSCRIPTION_DURATION_DAYS} дней

🎯 **Что включено:**
• Возможность добавлять пользовательские триггеры

💡 Выберите удобный способ оплаты ниже."""

    def get_premium_features_list(self) -> list:
        """Получить список премиум-функций"""
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
                session.query(Subscription)
                .filter(Subscription.expires_at > now)
                .all()
            )
        return {sub.tg_chat_id: sub for sub in subs}

    @staticmethod
    def create_subscription_keyboard(message):
        """Создать клавиатуру с вариантами оплаты"""
        buttons = []

        for sub_type, price in SubscriptionManager.get_types_dict().items():
            if sub_type == SubscriptionType.YOOKASSA:
                text = f"💳 Оплатить {price} ₽ (карта/ЮMoney)"
            elif sub_type == SubscriptionType.TELEGRAM_STARS:
                text = f"⭐ Оплатить {price} звёздочку"

            # КОРОТКИЙ callback_data!
            button = InlineKeyboardButton(
                text=text,
                callback_data=f"buy_sub:{message.from_user.id}:{message.chat.id}:{sub_type.value}",
            )
            buttons.append([button])

        # Кнопка информации (тоже короткая)
        info_button = InlineKeyboardButton(
            text="ℹ️ Информация о подписке",
            callback_data=f"sub_info:{message.chat.id}",
        )
        buttons.append([info_button])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

