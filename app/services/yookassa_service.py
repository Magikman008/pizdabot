"""
Сервис для работы с ЮKassa API
"""

import uuid
from typing import Optional, Tuple
from yookassa import Configuration, Payment

import settings
from app.logger import logger


class YooKassaService:
    """Сервис для работы с API ЮКасса"""

    def __init__(self):
        """Инициализация конфигурации ЮКасса"""
        try:
            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
            logger.info("ЮКасса сервис инициализирован")
        except Exception as e:
            logger.error(f"Ошибка инициализации ЮКасса: {e}")

    def create_payment(
        self,
        amount: float,
        description: str,
        return_url: str,
        metadata: dict = None,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Создать платёж в ЮКасса"""
        try:
            idempotence_key = str(uuid.uuid4())

            payment = Payment.create(
                {
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": "RUB"
                    },
                    "confirmation": {
                        "type": "redirect",
                        "return_url": return_url
                    },
                    "capture": True,
                    "description": description,
                    "metadata": metadata or {}
                },
                idempotence_key
            )

            confirmation_url = payment.confirmation.confirmation_url
            payment_id = payment.id

            logger.info(f"Создан платёж ЮКасса: {payment_id}, сумма: {amount} руб.")
            return True, confirmation_url, payment_id

        except Exception as e:
            logger.error(f"Ошибка создания платежа ЮКасса: {e}")
            return False, None, None

    def check_payment_status(self, payment_id: str) -> Tuple[bool, str]:
        """Проверить статус платежа"""
        try:
            payment = Payment.find_one(payment_id)
            status = payment.status
            is_paid = status == "succeeded"
            logger.info(f"Статус платежа {payment_id}: {status}")
            return is_paid, status
        except Exception as e:
            logger.error(f"Ошибка проверки статуса {payment_id}: {e}")
            return False, "error"

    def get_payment_info(self, payment_id: str) -> Optional[dict]:
        """Получить информацию о платеже"""
        try:
            payment = Payment.find_one(payment_id)
            return {
                "id": payment.id,
                "status": payment.status,
                "amount": float(payment.amount.value),
                "currency": payment.amount.currency,
                "metadata": payment.metadata,
            }
        except Exception as e:
            logger.error(f"Ошибка получения info {payment_id}: {e}")
            return None


yookassa_service = YooKassaService()
