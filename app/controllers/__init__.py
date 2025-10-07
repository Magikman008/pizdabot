from app.db import SessionLocal
from .admin_notifier import AdminNotifier
from .chat_info_manager import ChatInfoManager
from .chat_settings import ChatSettingsManager
from .feedback_manager import FeedbackManager
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
    "admin_notifier",
    "feedback_manager",
    "AdminNotifier",
    "FeedbackManager",
    "ChatInfoManager",
    "chat_info_manager",
]

# Создаем глобальный экземпляр менеджера настроек
chat_settings_manager = ChatSettingsManager(SessionLocal)

# Создаем глобальный экземпляр статистики
bot_stats = BotStatistics(SessionLocal)

# Создаем глобальный экземпляр менеджера подписок
subscription_manager = SubscriptionManager(SessionLocal)

# Создаем глобальный экземпляр менеджера
user_trigger_manager = UserTriggerManager(SessionLocal)

admin_notifier = AdminNotifier(SessionLocal)

feedback_manager = FeedbackManager(SessionLocal)

chat_info_manager = ChatInfoManager(SessionLocal)
