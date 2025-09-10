from aiogram import Router

from app.handlers import triggers
from app.handlers.commands import commands_router
from app.handlers.feedback import feedback_router

router = Router()
router.include_router(commands_router)
router.include_router(triggers.base_trigger_router)
router.include_router(feedback_router)

__all__ = ["router"]
