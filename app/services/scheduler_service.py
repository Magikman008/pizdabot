import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.executors.asyncio import AsyncIOExecutor
from app.controllers import chat_info_manager

logger = logging.getLogger(__name__)


# Функция обновления информации о чатах
async def hourly_chat_info_update():
    """Задача для регулярного обновления информации о чатах — каждый час по «реальному» часу."""
    logger.info("🔄 Запуск ежечасного обновления chat_info")
    start_time = datetime.now()

    try:
        # 1. Обновляем информацию о всех чатах
        stats = await chat_info_manager.update_all_chats_info()
        logger.info(
            f"📊 Обновлено {stats['updated']} чатов; "
            f"деактивировано {stats['deactivated']}; "
            f"ошибок {stats['errors']}"
        )

        # 2. Сохраняем снапшот в chat_info_history
        success = await chat_info_manager.save_hourly_snapshot()
        if success:
            logger.info("💾 Сохранён снапшот chat_info_history")
        else:
            logger.error("❌ Не удалось сохранить снапшот chat_info_history")

        execution_time = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Ежечасная задача завершена за {execution_time:.1f} сек")

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        logger.error(
            f"❌ Ошибка в hourly_chat_info_update (за {execution_time:.1f} сек): {e}"
        )


class SchedulerService:
    def __init__(self):
        executors = {"default": AsyncIOExecutor()}
        job_defaults = {
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 300,  # Грейс-тайм 5 минут
        }
        self.scheduler = AsyncIOScheduler(
            executors=executors, job_defaults=job_defaults, timezone="UTC"
        )

    async def start(self):
        """Запуск планировщика с крон-задачей на каждый час в XX:00 UTC."""
        try:
            self.scheduler.start()

            # Основная задача: каждый час, в минуту 0
            self.scheduler.add_job(
                func=hourly_chat_info_update,
                trigger="cron",
                minute=0,  # запуск в XX:00
                id="hourly_chat_info_update",
                replace_existing=True,
            )

            # Логирование запущенных задач
            jobs = self.scheduler.get_jobs()
            logger.info(f"🚀 Планировщик запущен успешно с {len(jobs)} задачами:")
            for job in jobs:
                next_run = (
                    job.next_run_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                    if job.next_run_time
                    else "Не запланировано"
                )
                logger.info(f"  📋 {job.id} — следующий запуск: {next_run}")

        except Exception as e:
            logger.error(f"❌ Ошибка запуска планировщика: {e}")

    async def stop(self):
        """Остановка планировщика."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("⏹️ Планировщик остановлен")

    def get_job_status(self) -> dict:
        """Получить статус всех запланированных задач."""
        if not self.scheduler.running:
            return {"status": "stopped", "jobs": []}

        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append(
                {
                    "id": job.id,
                    "name": job.name or job.id,
                    "next_run": (
                        job.next_run_time.isoformat() if job.next_run_time else None
                    ),
                    "trigger": str(job.trigger),
                }
            )

        return {"status": "running", "total_jobs": len(jobs_info), "jobs": jobs_info}

    async def run_job_manually(self, job_id: str) -> bool:
        """Ручной запуск конкретной задачи."""
        try:
            job = self.scheduler.get_job(job_id)
            if job:
                job.modify(next_run_time=datetime.now())
                logger.info(
                    f"🔧 Задача {job_id} запланирована к немедленному выполнению"
                )
                return True
            else:
                logger.warning(f"⚠️ Задача {job_id} не найдена")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка при ручном запуске задачи {job_id}: {e}")
            return False


# Глобальный экземпляр планировщика
scheduler_service = SchedulerService()
