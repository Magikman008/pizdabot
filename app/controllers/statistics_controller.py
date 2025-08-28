"""
Модуль для работы со статистикой бота
Отслеживает количество подъёбов, пользователей и групп
"""

from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import select, func, desc

from app.models import RoastWord, RoastEvent


class BotStatistics:
    def __init__(self, session_maker):
        """
        Инициализация класса статистики

        Args:
            session_maker: sessionmaker SQLAlchemy
        """
        self.session_maker = session_maker

    def __get_or_create_word(self, word: str) -> RoastWord:
        word_clean = word.lower().strip()
        with self.session_maker() as session:
            db_word = session.scalar(
                select(RoastWord).where(RoastWord.word == word_clean)
            )
            if not db_word:
                db_word = RoastWord(word=word_clean)
                session.add(db_word)
                session.commit()
                session.refresh(db_word)
            return db_word

    def add_roast(self, user_id: int, chat_id: int, trigger: str):
        """
        Добавить событие прожарки
        """
        db_word = self.__get_or_create_word(trigger)
        with self.session_maker() as session:
            event = RoastEvent(
                chat_id=chat_id,
                user_id=user_id,
                word_id=db_word.id,
                created_at=datetime.now(),
            )
            session.add(event)
            session.commit()

    def get_total_stats(
            self, chat_id: int | None = None
    ) -> Dict[str, int | str | None]:
        """
        Общая статистика:
        - всего прожарок
        - количество прожаренных пользователей
        - количество дней с прожарками
        - дата первой прожарки
        - количество уникальных чатов (только если chat_id=None)
        """
        with self.session_maker() as session:
            total_roasts_stmt = select(func.count(RoastEvent.id))
            unique_users_stmt = select(func.count(func.distinct(RoastEvent.user_id)))
            days_active_stmt = select(
                func.count(func.distinct(func.date(RoastEvent.created_at)))
            )
            first_roast_stmt = (
                select(RoastEvent.created_at)
                .order_by(RoastEvent.created_at.asc())
                .limit(1)
            )

            if chat_id is not None:
                total_roasts_stmt = total_roasts_stmt.where(RoastEvent.chat_id == chat_id)
                unique_users_stmt = unique_users_stmt.where(RoastEvent.chat_id == chat_id)
                days_active_stmt = days_active_stmt.where(RoastEvent.chat_id == chat_id)
                first_roast_stmt = first_roast_stmt.where(RoastEvent.chat_id == chat_id)

            total_roasts = session.scalar(total_roasts_stmt)
            unique_users = session.scalar(unique_users_stmt)
            days_active = session.scalar(days_active_stmt)
            first_roast = session.scalar(first_roast_stmt)

            # считаем количество уникальных чатов только если chat_id не задан
            unique_chats = None
            if chat_id is None:
                unique_chats = session.scalar(
                    select(func.count(func.distinct(RoastEvent.chat_id)))
                )

        result = {
            "total_roasts": total_roasts or 0,
            "total_roasted_users": unique_users or 0,
            "days_active": days_active or 0,
            "first_roast": first_roast.isoformat() if first_roast else None,
        }

        if chat_id is None:
            result["unique_chats"] = unique_chats or 0

        return result

    def get_top_triggers(
        self, chat_id: int | None = None, limit: int = 10
    ) -> Dict[str, int]:
        """
        Топ триггеров по количеству срабатываний в конкретном чате
        """
        with self.session_maker() as session:
            stmt = (
                select(RoastWord.word, func.count(RoastEvent.id).label("cnt"))
                .join(RoastEvent)
                .group_by(RoastWord.id)
                .order_by(desc("cnt"))
                .limit(limit)
            )

            if chat_id:
                stmt = stmt.where(RoastEvent.chat_id == chat_id)

            result = session.execute(stmt).all()

        return {word: count for word, count in result}

    def get_daily_stats(
            self, chat_id: int | None = None, days: int = 1
    ) -> list[dict[str, int | str]]:
        """
        Статистика по дням.
        - Если days=1 — возвращает только сегодня
        - Если days>1 — возвращает статистику за последние N дней
        - Если chat_id=None — считаем по всем чатам
        """
        end = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        start = end - timedelta(days=days)

        with self.session_maker() as session:
            stmt = (
                select(
                    func.date(RoastEvent.created_at).label("day"),
                    func.count(RoastEvent.id).label("roasts"),
                    func.count(func.distinct(RoastEvent.user_id)).label("unique_users"),
                )
                .where(RoastEvent.created_at >= start)
                .where(RoastEvent.created_at < end)
                .group_by(func.date(RoastEvent.created_at))
                .order_by(func.date(RoastEvent.created_at))
            )

            if chat_id is not None:
                stmt = stmt.where(RoastEvent.chat_id == chat_id)

            result = session.execute(stmt).all()

        # приводим к нормальному виду
        return [
            {"date": str(day), "roasts": roasts, "unique_users": users}
            for day, roasts, users in result
        ]

    def get_chat_stats_summary(self, chat_id: int) -> str:
        """Получить текстовое резюме статистики"""
        total = self.get_total_stats(chat_id)
        last_days = self.get_daily_stats(chat_id, days=3)
        top_triggers = self.get_top_triggers(chat_id, 5)

        summary = f"""📊 Статистика бота

🔥 Всего подъёбов: {total['total_roasts']}
👥 Пользователей подъёбано: {total['total_roasted_users']}
📅 Дней активности: {total['days_active']}

Последние 3 дня:"""

        for day in last_days:
            summary += f"\n{day['date']}: 🔥 {day['roasts']}"

        summary += "\n\nТоп-5 триггеров:"

        for i, (trigger, count) in enumerate(top_triggers.items(), 1):
            summary += f"\n{i}. '{trigger}' - {count} раз"

        return summary

    def get_admin_stats(self) -> str:
        """Получить детальную статистику для админов"""
        total = self.get_total_stats()
        top_triggers = self.get_top_triggers(limit=30)
        last_days = self.get_daily_stats(days=7)

        detailed = f"""📊 Статистика по всем чатам

🔥 Всего подъёбов: {total['total_roasts']}
👥 Уникальных пользователей: {total['total_roasted_users']}
💬 Уникальных групп: {total['unique_chats']}
📅 Дней активности: {total['days_active']}

Активность за последние 7 дней:"""

        for day in last_days:
            detailed += f"\n{day['date']}: 🔥 {day['roasts']} 👥 {day['unique_users']}"

        detailed += "\n\nТоп-10 триггеров:"
        for i, (trigger, count) in enumerate(top_triggers.items(), 1):
            detailed += f"\n{i}. '{trigger}' - {count} раз"

        return detailed
