"""
Инициализация всех обработчиков команд
Подключает все роутеры включая обновленную систему обратной связи
"""
from aiogram import Router

from app.handlers import triggers
from app.handlers.commands import commands_router
from app.handlers.feedback import feedback_router

# Создаем главный роутер
router = Router()

# Подключаем все роутеры в правильном порядке
# Порядок важен! Более специфичные обработчики должны быть первыми
router.include_router(feedback_router)      # Система обратной связи
router.include_router(commands_router)      # Остальные команды бота
router.include_router(triggers.base_trigger_router)  # Триггеры и ответы

__all__ = ["router"]