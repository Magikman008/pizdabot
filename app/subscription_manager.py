"""
Модуль для управления подписками через Telegram Stars
Позволяет пользователям покупать подписки за звёздочки Telegram
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


class SubscriptionManager:
    def __init__(self, subscriptions_file: str = "subscriptions.json"):
        """
        Инициализация менеджера подписок

        Args:
            subscriptions_file (str): Путь к файлу с подписками
        """
        self.subscriptions_file = subscriptions_file
        self.data = self._load_subscriptions()
        self.data.setdefault("subscriptions", {})
        self.data.setdefault("transactions", {})

        # Настройки подписки
        self.SUBSCRIPTION_PRICE_STARS = 1  # Цена подписки в звёздочках
        self.SUBSCRIPTION_DURATION_DAYS = 30  # Длительность подписки в днях

    def _load_subscriptions(self) -> Dict[str, Any]:
        """Загрузка подписок из файла"""
        if not os.path.exists(self.subscriptions_file):
            return {
                "subscriptions": {},  # Подписки по пользователям
                "transactions": {},  # История транзакций
                "version": "1.0",
            }

        try:
            with open(self.subscriptions_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Конвертируем даты обратно в datetime объекты
                for user_id, sub_data in data.get("subscriptions", {}).items():
                    if "expires_at" in sub_data and isinstance(
                        sub_data["expires_at"], str
                    ):
                        sub_data["expires_at"] = datetime.fromisoformat(
                            sub_data["expires_at"]
                        )
                return data
        except (json.JSONDecodeError, FileNotFoundError):
            return self._load_subscriptions()  # Возвращаем пустую структуру при ошибке

    def _save_subscriptions(self):
        """
        Сохранение подписок в файл.
        Конвертируем все datetime → ISO строки.
        """
        try:
            to_save = {
                "subscriptions": {},
                "transactions": self.data.get("transactions", {}),
                "version": "1.0",
            }
            for uid, sub in self.data.get("subscriptions", {}).items():
                copy_sub = sub.copy()
                # Преобразуем datetime в строки ISO
                if "activated_at" in copy_sub and isinstance(
                    copy_sub["activated_at"], datetime
                ):
                    copy_sub["activated_at"] = copy_sub["activated_at"].isoformat()
                if "expires_at" in copy_sub and isinstance(
                    copy_sub["expires_at"], datetime
                ):
                    copy_sub["expires_at"] = copy_sub["expires_at"].isoformat()
                to_save["subscriptions"][uid] = copy_sub

            with open(self.subscriptions_file, "w", encoding="utf-8") as f:
                json.dump(to_save, f, ensure_ascii=False, indent=2)

            print(f"DEBUG: Подписки успешно сохранены в {self.subscriptions_file}")
        except Exception as e:
            print(f"ОШИБКА: Не удается сохранить подписки: {e}")

    def has_active_subscription(self, user_id: int) -> bool:
        """
        Проверить, есть ли у пользователя активная подписка

        Args:
            user_id: ID пользователя

        Returns:
            bool: True если подписка активна
        """
        user_str = str(user_id)

        if user_str not in self.data["subscriptions"]:
            return False

        sub_data = self.data["subscriptions"][user_str]
        expires_at = sub_data.get("expires_at")

        if not expires_at:
            return False

        # Если expires_at строка, конвертируем в datetime
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
            self.data["subscriptions"][user_str]["expires_at"] = expires_at

        return expires_at > datetime.now()

    def get_subscription_info(self, user_id: int) -> str:
        """
        Получить информацию о подписке пользователя

        Args:
            user_id: ID пользователя

        Returns:
            str: Информация о подписке
        """
        user_str = str(user_id)

        if not self.has_active_subscription(user_id):
            return f"""⭐ **Информация о подписке:**

❌ Подписка неактивна
💰 Цена: {self.SUBSCRIPTION_PRICE_STARS} звёздочка
⏱️ Длительность: {self.SUBSCRIPTION_DURATION_DAYS} дней

💡 Используйте /sub для покупки подписки!"""

        sub_data = self.data["subscriptions"][user_str]
        expires_at = sub_data["expires_at"]

        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        days_left = (expires_at - datetime.now()).days

        return f"""⭐ **Информация о подписке:**

✅ Подписка активна
📅 Истекает: {expires_at.strftime('%d.%m.%Y %H:%M')}
⏰ Осталось дней: {days_left}
🎯 Статус: Премиум-пользователь"""

    def activate_subscription(
        self, user_id: int, transaction_id: str = None
    ) -> Tuple[bool, str]:
        """
        Активировать подписку пользователя

        Args:
            user_id: ID пользователя
            transaction_id: ID транзакции (опционально)

        Returns:
            tuple: (успешно ли, сообщение)
        """
        user_str = str(user_id)
        now = datetime.now()

        # Если у пользователя уже есть активная подписка, продлеваем её
        if self.has_active_subscription(user_id):
            current_expiry = self.data["subscriptions"][user_str]["expires_at"]
            if isinstance(current_expiry, str):
                current_expiry = datetime.fromisoformat(current_expiry)
            new_expiry = current_expiry + timedelta(
                days=self.SUBSCRIPTION_DURATION_DAYS
            )
        else:
            new_expiry = now + timedelta(days=self.SUBSCRIPTION_DURATION_DAYS)

        # Создаем или обновляем подписку
        self.data["subscriptions"][user_str] = {
            "user_id": user_id,
            "activated_at": now,
            "expires_at": new_expiry,
            "transaction_id": transaction_id,
            "price_stars": self.SUBSCRIPTION_PRICE_STARS,
        }

        # Сохраняем транзакцию
        if transaction_id:
            self.data["transactions"][transaction_id] = {
                "user_id": user_id,
                "amount_stars": self.SUBSCRIPTION_PRICE_STARS,
                "timestamp": now.isoformat(),
                "type": "subscription_purchase",
            }

        self._save_subscriptions()

        return (
            True,
            f"""✅ **Подписка активирована!**

⭐ Оплачено: {self.SUBSCRIPTION_PRICE_STARS} звёздочка
📅 Действует до: {new_expiry.strftime('%d.%m.%Y %H:%M')}
🎯 Статус: Премиум-пользователь

🚀 Теперь вам доступны все премиум-функции бота!""",
        )

    def create_subscription_keyboard(self) -> InlineKeyboardMarkup:
        """
        Создать клавиатуру для покупки подписки

        Returns:
            InlineKeyboardMarkup: Клавиатура с кнопками
        """
        # Используем InlineKeyboardBuilder для aiogram 3.x
        builder = InlineKeyboardBuilder()

        # Кнопка покупки подписки за звёздочки
        buy_button = InlineKeyboardButton(
            text=f"⭐ Купить подписку за {self.SUBSCRIPTION_PRICE_STARS} звёздочку",
            callback_data=f"buy_subscription:{self.SUBSCRIPTION_PRICE_STARS}",
        )

        # Кнопка информации
        info_button = InlineKeyboardButton(
            text="ℹ️ Информация о подписке", callback_data="subscription_info"
        )

        # Добавляем кнопки (каждая в своем ряду)
        builder.add(buy_button)
        builder.add(info_button)

        # Устанавливаем ширину строки
        builder.adjust(1)

        return builder.as_markup()

    def get_subscription_description(self) -> str:
        """
        Получить описание подписки

        Returns:
            str: Описание подписки
        """
        return f"""⭐ **Премиум-подписка PizdaBot**

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

    def cleanup_expired_subscriptions(self) -> int:
        """
        Очистить истёкшие подписки

        Returns:
            int: Количество удалённых подписок
        """
        expired_count = 0
        now = datetime.now()
        users_to_remove = []

        for user_str, sub_data in self.data["subscriptions"].items():
            expires_at = sub_data.get("expires_at")

            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)

            if expires_at <= now:
                users_to_remove.append(user_str)
                expired_count += 1

        for user_str in users_to_remove:
            del self.data["subscriptions"][user_str]

        if expired_count > 0:
            self._save_subscriptions()
            print(f"DEBUG: Удалено {expired_count} истёкших подписок")

        return expired_count

    def get_all_subscribers(self) -> Dict[str, Dict]:
        """
        Получить всех активных подписчиков

        Returns:
            Dict: Словарь активных подписчиков
        """
        active_subscribers = {}
        now = datetime.now()

        for user_str, sub_data in self.data["subscriptions"].items():
            expires_at = sub_data.get("expires_at")

            if isinstance(expires_at, str):
                expires_at = datetime.fromisoformat(expires_at)

            if expires_at > now:
                active_subscribers[user_str] = sub_data

        return active_subscribers


# Создаем глобальный экземпляр менеджера подписок
subscription_manager = SubscriptionManager()
