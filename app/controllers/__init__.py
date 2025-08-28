from app.db import SessionLocal
from .chat_settings import ChatSettingsManager
from .statistics_controller import BotStatistics
from .subscription_manager import SubscriptionManager
from .user_triggers import UserTriggerManager

__all__ = [
    "ChatSettingsManager",
    "BotStatistics",
    "SubscriptionManager",
    "UserTriggerManager",
    "chat_settings_manager",
    "bot_stats",
    "subscription_manager",
    "user_trigger_manager",
]

# Создаем глобальный экземпляр менеджера настроек
chat_settings_manager = ChatSettingsManager(SessionLocal)


# Создаем глобальный экземпляр статистики
bot_stats = BotStatistics(SessionLocal)

# Создаем глобальный экземпляр менеджера подписок
subscription_manager = SubscriptionManager(SessionLocal)

# Создаем глобальный экземпляр менеджера
user_trigger_manager = UserTriggerManager(SessionLocal)
