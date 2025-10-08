from aiogram import Router
from app.handlers.commands import (
    admin_tools,
    chat_settings,
    chat_stats,
    custom_triggers,
    help_commands,
    subscription, nps_commands,
)
from app.handlers import chat_membership

commands_router = Router()
commands_router.include_router(admin_tools.admin_router)
commands_router.include_router(chat_settings.chat_settings_router)
commands_router.include_router(chat_stats.chat_stats_router)
commands_router.include_router(custom_triggers.custom_triggers_router)
commands_router.include_router(help_commands.help_router)
commands_router.include_router(subscription.subscription_router)
commands_router.include_router(chat_membership.chat_membership_router)
commands_router.include_router(nps_commands.nps_router)

__all__ = ["commands_router"]
