import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor

from app.controllers import chat_info_manager

logger = logging.getLogger(__name__)


# Выносим функции обновления за пределы класса
async def minutely_chat_info_update():
    """Задача для тестирования - обновление каждую минуту"""
    logger.info("Запуск тестового обновления chat_info (каждую минуту)")

    start_time = datetime.now()
    try:
        # 1. Обновляем информацию о всех чатах
        stats = await chat_info_manager.update_all_chats_info()
        logger.info(
            f"Обновлено {stats['updated']} чатов; деактивировано {stats['deactivated']}")

        # 2. Сохраняем снапшот в chat_info_history
        success = await chat_info_manager.save_hourly_snapshot()
        if success:
            logger.info("Сохранен снапшот chat_info_history")
        else:
            logger.error("Не удалось сохранить снапшот chat_info_history")

        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"Задача завершена за {execution_time:.1f} сек")

    except Exception as e:
        logger.error(f"Ошибка в hourly_chat_info_update: {e}")


class SchedulerService:
    def __init__(self):
        executors = {
            'default': AsyncIOExecutor()
        }

        job_defaults = {
            'coalesce': True,
            'max_instances': 1,
            'misfire_grace_time': 30
        }

        self.scheduler = AsyncIOScheduler(
            executors=executors,
            job_defaults=job_defaults,
            timezone='UTC'
        )

    async def start(self):
        """Запуск планировщика"""
        try:
            self.scheduler.start()

            # ДЛЯ ТЕСТИРОВАНИЯ: каждую минуту
            self.scheduler.add_job(
                func=minutely_chat_info_update,  # Функция, а не метод
                trigger='interval',
                minutes=1,
                id='minutely_chat_info_update',
                replace_existing=True
            )

            logger.info("Планировщик запущен успешно")

        except Exception as e:
            logger.error(f"Ошибка запуска планировщика: {e}")

    async def stop(self):
        """Остановка планировщика"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Планировщик остановлен")


# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()
