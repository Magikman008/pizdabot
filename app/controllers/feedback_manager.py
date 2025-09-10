"""
Менеджер обратной связи - управление сообщениями пользователей
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.feedback import Base, Feedback
from settings import DATABASE_URL

class FeedbackManager:
    """Класс для управления обратной связью пользователей"""

    def __init__(self):
        # Инициализация базы данных
        self.engine = create_engine(DATABASE_URL, echo=False)
        self.Session = sessionmaker(bind=self.engine)

        # Создаем таблицы если их нет
        Base.metadata.create_all(self.engine)
        print("Feedback: используем MySQL базу данных")

    def add_feedback(self, user_id: int, username: str, first_name: str,
                    last_name: str, message: str) -> Optional[int]:
        """
        Добавить новое сообщение обратной связи

        Args:
            user_id: ID пользователя в Telegram
            username: Username пользователя (без @)
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            message: Текст сообщения

        Returns:
            Optional[int]: ID созданной записи или None при ошибке
        """
        try:
            with self.Session() as session:
                feedback = Feedback(
                    user_id=user_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    message=message
                )
                session.add(feedback)
                session.commit()
                session.refresh(feedback)
                return feedback.id
        except Exception as e:
            print(f"Ошибка при добавлении feedback: {e}")
            return None

    def get_all_feedback(self, limit: int = 50, unread_only: bool = False) -> List[Dict[Any, Any]]:
        """
        Получить все сообщения обратной связи

        Args:
            limit: Максимальное количество сообщений
            unread_only: Только непрочитанные сообщения

        Returns:
            List[Dict]: Список сообщений
        """
        try:
            with self.Session() as session:
                query = session.query(Feedback)

                if unread_only:
                    query = query.filter(Feedback.is_read == False)

                feedbacks = query.order_by(
                    Feedback.created_at.desc()
                ).limit(limit).all()

                return [feedback.to_dict() for feedback in feedbacks]
        except Exception as e:
            print(f"Ошибка при получении feedback: {e}")
            return []

    def get_unread_count(self) -> int:
        """
        Получить количество непрочитанных сообщений

        Returns:
            int: Количество непрочитанных сообщений
        """
        try:
            with self.Session() as session:
                count = session.query(Feedback).filter(
                    Feedback.is_read == False
                ).count()
                return count
        except Exception as e:
            print(f"Ошибка при подсчете непрочитанных: {e}")
            return 0

    def mark_as_read(self, feedback_id: int) -> bool:
        """
        Отметить сообщение как прочитанное

        Args:
            feedback_id: ID сообщения

        Returns:
            bool: True если успешно обновлено
        """
        try:
            with self.Session() as session:
                feedback = session.query(Feedback).filter(
                    Feedback.id == feedback_id
                ).first()

                if feedback:
                    feedback.is_read = True
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"Ошибка при отметке как прочитанное: {e}")
            return False

    def mark_all_as_read(self) -> int:
        """
        Отметить все сообщения как прочитанные

        Returns:
            int: Количество обновленных записей
        """
        try:
            with self.Session() as session:
                result = session.query(Feedback).filter(
                    Feedback.is_read == False
                ).update({'is_read': True}, synchronize_session=False)
                session.commit()
                return result
        except Exception as e:
            print(f"Ошибка при отметке всех как прочитанные: {e}")
            return 0

    def get_feedback_by_id(self, feedback_id: int) -> Optional[Dict[Any, Any]]:
        """
        Получить сообщение по ID

        Args:
            feedback_id: ID сообщения

        Returns:
            Optional[Dict]: Данные сообщения или None
        """
        try:
            with self.Session() as session:
                feedback = session.query(Feedback).filter(
                    Feedback.id == feedback_id
                ).first()

                if feedback:
                    return feedback.to_dict()
                return None
        except Exception as e:
            print(f"Ошибка при получении feedback по ID: {e}")
            return None

    def delete_feedback(self, feedback_id: int) -> bool:
        """
        Удалить сообщение обратной связи

        Args:
            feedback_id: ID сообщения

        Returns:
            bool: True если успешно удалено
        """
        try:
            with self.Session() as session:
                feedback = session.query(Feedback).filter(
                    Feedback.id == feedback_id
                ).first()

                if feedback:
                    session.delete(feedback)
                    session.commit()
                    return True
                return False
        except Exception as e:
            print(f"Ошибка при удалении feedback: {e}")
            return False

    def get_feedback_by_user(self, user_id: int, limit: int = 20) -> List[Dict[Any, Any]]:
        """
        Получить все сообщения конкретного пользователя

        Args:
            user_id: ID пользователя
            limit: Максимальное количество сообщений

        Returns:
            List[Dict]: Список сообщений пользователя
        """
        try:
            with self.Session() as session:
                feedbacks = session.query(Feedback).filter(
                    Feedback.user_id == user_id
                ).order_by(
                    Feedback.created_at.desc()
                ).limit(limit).all()

                return [feedback.to_dict() for feedback in feedbacks]
        except Exception as e:
            print(f"Ошибка при получении feedback пользователя: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по обращениям

        Returns:
            Dict: Статистика обращений
        """
        try:
            with self.Session() as session:
                total_count = session.query(Feedback).count()
                unread_count = session.query(Feedback).filter(
                    Feedback.is_read == False
                ).count()

                # Подсчет уникальных пользователей
                unique_users = session.query(Feedback.user_id).distinct().count()

                # Последнее обращение
                last_feedback = session.query(Feedback).order_by(
                    Feedback.created_at.desc()
                ).first()

                return {
                    'total_count': total_count,
                    'unread_count': unread_count,
                    'read_count': total_count - unread_count,
                    'unique_users': unique_users,
                    'last_feedback_date': last_feedback.created_at.isoformat() if last_feedback else None
                }
        except Exception as e:
            print(f"Ошибка при получении статистики: {e}")
            return {
                'total_count': 0,
                'unread_count': 0,
                'read_count': 0,
                'unique_users': 0,
                'last_feedback_date': None
            }

# Глобальный экземпляр менеджера
feedback_manager = FeedbackManager()
