"""
Менеджер системы обратной связи - полностью переписанная реализация
Управление обращениями пользователей с использованием существующей архитектуры проекта
"""
from contextlib import contextmanager
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from sqlalchemy import desc, func

from app.models.feedback import Feedback


class FeedbackManager:
    """
    Менеджер для работы с системой обратной связи
    Использует существующую инфраструктуру БД проекта
    """

    def __init__(self, session_maker):
        self.session_maker = session_maker
        print("📝 FeedbackManager: Подключен к существующей БД")

    @contextmanager
    def get_session(self):
        """
        Контекстный менеджер для работы с сессией БД
        """
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"❌ Ошибка БД: {e}")
            raise
        finally:
            session.close()

    def add_feedback(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        message: str = ""
    ) -> Optional[int]:
        """
        Добавить новое обращение пользователя

        Args:
            user_id: Telegram ID пользователя
            username: Username без @
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            message: Текст обращения

        Returns:
            Optional[int]: ID созданного обращения или None при ошибке
        """
        if not message or not message.strip():
            print("❌ Пустое сообщение обращения")
            return None

        try:
            with self.get_session() as session:
                feedback = Feedback(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    message=message.strip()
                )

                session.add(feedback)
                session.flush()  # Получаем ID без коммита
                feedback_id = feedback.id

                print(f"✅ Создано обращение #{feedback_id} от пользователя {user_id}")
                return feedback_id

        except Exception as e:
            print(f"❌ Ошибка создания обращения: {e}")
            return None

    def get_all_feedback(
        self,
        limit: int = 50,
        unread_only: bool = False,
        user_id: Optional[int] = None
    ):
        """
        Получить список обращений

        Args:
            limit: Максимальное количество записей
            unread_only: Только непрочитанные обращения
            user_id: Фильтр по конкретному пользователю

            List[Feedback]: Список обращений
        """
        try:
            with self.get_session() as session:
                query = session.query(Feedback)

                # Применяем фильтры
                if unread_only:
                    query = query.filter(Feedback.is_read == False)

                if user_id:
                    query = query.filter(Feedback.user_id == user_id)

                # Сортируем по дате создания (новые первые)
                feedbacks = query.order_by(desc(Feedback.created_at)).limit(limit).all()

                result = [feedback for feedback in feedbacks]
                print(f"📋 Получено {len(result)} обращений (лимит: {limit})")
                return result

        except Exception as e:
            print(f"❌ Ошибка получения обращений: {e}")
            return []

    def get_feedback_by_id(self, feedback_id: int) -> Optional[Dict[str, Any]]:
        """
        Получить обращение по ID

        Args:
            feedback_id: ID обращения

        Returns:
            Optional[Dict]: Данные обращения или None
        """
        try:
            with self.get_session() as session:
                feedback = session.query(Feedback).filter(
                    Feedback.id == feedback_id
                ).first()

                if feedback:
                    print(f"📋 Получено обращение #{feedback_id}")
                    return feedback

                print(f"❌ Обращение #{feedback_id} не найдено")
                return None

        except Exception as e:
            print(f"❌ Ошибка получения обращения #{feedback_id}: {e}")
            return None

    def mark_as_read(self, feedback_id: int) -> bool:
        """
        Отметить обращение как прочитанное

        Args:
            feedback_id: ID обращения

        Returns:
            bool: True если успешно обновлено
        """
        try:
            with self.get_session() as session:
                feedback = session.query(Feedback).filter(
                    Feedback.id == feedback_id
                ).first()

                if feedback and not feedback.is_read:
                    feedback.mark_as_read()
                    print(f"👁️ Обращение #{feedback_id} отмечено как прочитанное")
                    return True

                return False

        except Exception as e:
            print(f"❌ Ошибка отметки обращения #{feedback_id}: {e}")
            return False

    def mark_all_as_read(self) -> int:
        """
        Отметить все непрочитанные обращения как прочитанные

        Returns:
            int: Количество обновленных записей
        """
        try:
            with self.get_session() as session:
                updated_count = session.query(Feedback).filter(
                    Feedback.is_read == False
                ).update(
                    {'is_read': True},
                    synchronize_session=False
                )

                print(f"👁️ Отмечено как прочитанные: {updated_count} обращений")
                return updated_count

        except Exception as e:
            print(f"❌ Ошибка массовой отметки обращений: {e}")
            return 0

    def get_unread_count(self) -> int:
        """
        Получить количество непрочитанных обращений

        Returns:
            int: Количество непрочитанных обращений
        """
        try:
            with self.get_session() as session:
                count = session.query(Feedback).filter(
                    Feedback.is_read == False
                ).count()

                return count

        except Exception as e:
            print(f"❌ Ошибка подсчета непрочитанных: {e}")
            return 0

    def get_feedback_by_user(self, user_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Получить все обращения конкретного пользователя

        Args:
            user_id: Telegram ID пользователя
            limit: Максимальное количество записей

        Returns:
            List[Dict]: Список обращений пользователя
        """
        return self.get_all_feedback(limit=limit, user_id=user_id)

    def delete_feedback(self, feedback_id: int) -> bool:
        """
        Удалить обращение по ID

        Args:
            feedback_id: ID обращения

        Returns:
            bool: True если успешно удалено
        """
        try:
            with self.get_session() as session:
                feedback = session.query(Feedback).filter(
                    Feedback.id == feedback_id
                ).first()

                if feedback:
                    session.delete(feedback)
                    print(f"🗑️ Удалено обращение #{feedback_id}")
                    return True

                print(f"❌ Обращение #{feedback_id} не найдено для удаления")
                return False

        except Exception as e:
            print(f"❌ Ошибка удаления обращения #{feedback_id}: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по обращениям

        Returns:
            Dict: Словарь со статистикой
        """
        try:
            with self.get_session() as session:
                # Основные счетчики
                total_count = session.query(Feedback).count()
                unread_count = session.query(Feedback).filter(
                    Feedback.is_read == False
                ).count()

                # Уникальные пользователи
                unique_users = session.query(func.count(func.distinct(Feedback.user_id))).scalar()

                # Последнее обращение
                last_feedback = session.query(Feedback).order_by(
                    desc(Feedback.created_at)
                ).first()

                # Статистика за последние 24 часа
                day_ago = datetime.utcnow() - timedelta(days=1)
                recent_count = session.query(Feedback).filter(
                    Feedback.created_at >= day_ago
                ).count()

                stats = {
                    'total_count': total_count,
                    'unread_count': unread_count,
                    'read_count': total_count - unread_count,
                    'unique_users': unique_users,
                    'last_feedback_date': last_feedback.created_at.isoformat() if last_feedback else None,
                    'recent_24h': recent_count
                }

                print(f"📊 Статистика: всего {total_count}, непрочитанных {unread_count}")
                return stats

        except Exception as e:
            print(f"❌ Ошибка получения статистики: {e}")
            return {
                'total_count': 0,
                'unread_count': 0,
                'read_count': 0,
                'unique_users': 0,
                'last_feedback_date': None,
                'recent_24h': 0
            }

    def cleanup_old_feedback(self, days_old: int = 90) -> int:
        """
        Очистка старых обращений (для обслуживания БД)

        Args:
            days_old: Возраст обращений в днях для удаления

        Returns:
            int: Количество удаленных записей
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)

            with self.get_session() as session:
                deleted_count = session.query(Feedback).filter(
                    Feedback.created_at < cutoff_date,
                    Feedback.is_read == True  # Удаляем только прочитанные
                ).delete(synchronize_session=False)

                print(f"🧹 Очищено {deleted_count} старых обращений (старше {days_old} дней)")
                return deleted_count

        except Exception as e:
            print(f"❌ Ошибка очистки старых обращений: {e}")
            return 0