"""
Модуль для работы со статистикой бота
Отслеживает количество подъёбов, пользователей и групп
"""

from datetime import datetime, timedelta
from typing import Dict

from sqlalchemy import select, func, desc
from sqlalchemy.sql.sqltypes import Integer

from app.models import RoastWord, RoastEvent
from app.models.chat_info import ChatInfo


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
         - количество уникальных чатов (по chat_info)
         - количество активных и неактивных чатов (по chat_info)
        """

        with self.session_maker() as session:
            # Подготовка запросов по RoastEvent
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
                total_roasts_stmt = total_roasts_stmt.where(
                    RoastEvent.chat_id == chat_id
                )
                unique_users_stmt = unique_users_stmt.where(
                    RoastEvent.chat_id == chat_id
                )
                days_active_stmt = days_active_stmt.where(RoastEvent.chat_id == chat_id)
                first_roast_stmt = first_roast_stmt.where(RoastEvent.chat_id == chat_id)

            # Выполнение запросов
            total_roasts = session.scalar(total_roasts_stmt) or 0
            unique_users = session.scalar(unique_users_stmt) or 0
            days_active = session.scalar(days_active_stmt) or 0
            first_roast_ts = session.scalar(first_roast_stmt)
            first_roast = first_roast_ts.isoformat() if first_roast_ts else None

            result = {
                "total_roasts": total_roasts,
                "total_roasted_users": unique_users,
                "days_active": days_active,
                "first_roast": first_roast,
            }

            # Статистика по chat_info только если общий вызов
            if chat_id is None:
                # Всего уникальных чатов в chat_info
                total_chats = session.scalar(select(func.count(ChatInfo.id))) or 0
                # Активные чаты
                active_chats = (
                    session.scalar(
                        select(func.count())
                        .select_from(ChatInfo)
                        .where(ChatInfo.is_active == True)
                    )
                    or 0
                )
                # Неактивные чаты
                inactive_chats = total_chats - active_chats

                result["total_chats"] = total_chats
                result["active_chats"] = active_chats
                result["inactive_chats"] = inactive_chats

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
        end = datetime.now().replace(
            hour=0, minute=0, second=0, microsecond=0
        ) + timedelta(days=1)
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
        """Получить текстовое резюме статистики по конкретному чату"""
        total = self.get_total_stats(chat_id)
        last_days = self.get_daily_stats(chat_id, days=3)
        top_triggers = self.get_top_triggers(chat_id, limit=5)

        # Форматируем дату первой прожарки
        first_roast = total.get("first_roast")
        if first_roast:
            try:
                dt = datetime.fromisoformat(first_roast)
                first_roast_str = dt.strftime("%d.%m.%Y %H:%M")
            except ValueError:
                first_roast_str = first_roast
        else:
            first_roast_str = "—"

        summary = f"""📊 Статистика бота в чате

🔥 Всего подъёбов: {total['total_roasts']}
👥 Пользователей подъёбано: {total['total_roasted_users']}
📅 Дней активности: {total['days_active']}"""

        summary += "\n\nПоследние 3 дня:"
        for day in last_days:
            summary += f"\n{day['date']}: 🔥 {day['roasts']}"

        summary += "\n\nТоп-5 триггеров:"
        for i, (trigger, count) in enumerate(top_triggers.items(), 1):
            summary += f"\n{i}. «{trigger}» – {count} раз"

        return summary

    def get_admin_stats(self) -> str:
        """Получить детальную статистику для админов по всем чатам"""

        total = self.get_total_stats()
        top_triggers = self.get_top_triggers(limit=30)
        last_days = self.get_daily_stats(days=7)

        # Получаем общее количество участников из всех групп
        with self.session_maker() as session:
            total_members = (
                session.scalar(
                    select(
                        func.sum(
                            func.cast(
                                func.regexp_replace(
                                    ChatInfo.members_count, r"[^0-9]", ""
                                ),
                                Integer,
                            )
                        )
                    ).where(
                        ChatInfo.is_active == True,
                        ChatInfo.members_count.regexp_match(r"^[0-9]+$"),
                        ChatInfo.chat_type.in_(["group", "supergroup"]),
                    )
                )
                or 0
            )

        detailed = f"""📊 Общая статистика по всем чатам

🔥 Всего подъёбов: {total['total_roasts']}
👥 Уникальных пользователей: {total['total_roasted_users']}
💬 Всего чатов: {total['total_chats']}
✅ Активных чатов: {total['active_chats']}
❌ Неактивных чатов: {total['inactive_chats']}
👫 Всего участников в группах: {total_members}
📅 Дней активности: {total['days_active']}"""

        detailed += "\n\nАктивность за последние 7 дней:"
        for day in last_days:
            detailed += f"\n{day['date']}: 🔥 {day['roasts']} 👥 {day['unique_users']}"

        detailed += "\n\nТоп-10 триггеров:"
        for i, (trigger, count) in enumerate(top_triggers.items(), 1):
            if i <= 10:  # Ограничиваем до 10
                detailed += f"\n{i}. «{trigger}» – {count} раз"

        return detailed
