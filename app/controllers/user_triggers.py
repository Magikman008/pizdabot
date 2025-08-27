"""
Модуль для управления пользовательскими триггерами
Позволяет участникам добавлять локальные триггеры для каждого чата
"""

import re
from datetime import date
from typing import Optional

from sqlalchemy import select, func

from app.models import CustomTrigger


class UserTriggerManager:
    # Настройки модерации
    MAX_TRIGGERS_PER_USER_PER_DAY = 3
    MAX_TRIGGERS_PER_CHAT = 50
    MIN_TRIGGER_LENGTH = 2
    MIN_RESPONSE_LENGTH = 1
    MAX_TRIGGER_LENGTH = 100
    MAX_RESPONSE_LENGTH = 500

    def __init__(self, session_maker):
        """
        Инициализация менеджера пользовательских триггеров

        Args:
            session_maker
        """
        self.session_maker = session_maker

    @staticmethod
    def _clean_text(text: str) -> str:
        """Очистка и нормализация текста"""
        return text.strip().lower()

    def _validate_trigger(self, trigger: str, response: str) -> Optional[str]:
        """
        Валидация триггера и ответа

        Returns:
            str: Сообщение об ошибке или None если все ок
        """
        # Проверяем длину триггера
        if len(trigger) < self.MIN_TRIGGER_LENGTH:
            return f"❌ Триггер слишком короткий (минимум {self.MIN_TRIGGER_LENGTH} символа)"

        if len(trigger) > self.MAX_TRIGGER_LENGTH:
            return f"❌ Триггер слишком длинный (максимум {self.MAX_TRIGGER_LENGTH} символов)"

        # Проверяем длину ответа
        if len(response) < self.MIN_RESPONSE_LENGTH:
            return (
                f"❌ Ответ слишком короткий (минимум {self.MIN_RESPONSE_LENGTH} символ)"
            )

        if len(response) > self.MAX_RESPONSE_LENGTH:
            return f"❌ Ответ слишком длинный (максимум {self.MAX_RESPONSE_LENGTH} символов)"

        # Проверяем на недопустимые символы в триггере
        if re.search(r'[/\\<>"|]', trigger):
            return '❌ Триггер содержит недопустимые символы: / \\ < > " |'

        return None

    def can_user_add_trigger(self, user_id: int, chat_id: int) -> tuple[bool, str]:
        """
        Проверяем лимиты:
        - глобально для пользователя на СЕГОДНЯ (как в твоём JSON-менеджере)
        - общее количество триггеров в конкретном чате
        """
        today = date.today()

        with self.session_maker() as session:
            # Сколько пользователь добавил СЕГОДНЯ во всех чатах (совпадает с прежней логикой)
            today_count = session.scalar(
                select(func.count())
                .select_from(CustomTrigger)
                .where(
                    CustomTrigger.author_id == user_id,
                    CustomTrigger.created == today,
                )
            ) or 0

            if today_count >= self.MAX_TRIGGERS_PER_USER_PER_DAY:
                return (
                    False,
                    f"❌ Вы уже добавили максимальное количество триггеров на сегодня "
                    f"({self.MAX_TRIGGERS_PER_USER_PER_DAY})",
                )

            # Сколько всего триггеров уже есть в чате
            chat_count = session.scalar(
                select(func.count())
                .select_from(CustomTrigger)
                .where(CustomTrigger.chat_id == chat_id)
            ) or 0

            if chat_count >= self.MAX_TRIGGERS_PER_CHAT:
                return (
                    False,
                    f"❌ В чате уже максимальное количество триггеров ({self.MAX_TRIGGERS_PER_CHAT})",
                )

            return True, ""


    def add_trigger(self, user_id: int, chat_id: int, trigger: str, response: str) -> tuple[bool, str]:
        error = self._validate_trigger(trigger, response)
        if error:
            return False, error

        can_add, msg = self.can_user_add_trigger(user_id, chat_id)
        if not can_add:
            return False, msg

        trigger_clean = self._clean_text(trigger)
        response_clean = self._clean_text(response)

        with self.session_maker() as session:
            exists = session.scalar(
                select(func.count())
                .select_from(CustomTrigger)
                .where(
                    CustomTrigger.chat_id == chat_id,
                    CustomTrigger.trigger_word == trigger_clean,
                )
            )

            if exists:
                return False, "❌ Такой триггер уже существует в этом чате"

            tr = CustomTrigger(
                trigger_word=trigger_clean,
                response=response_clean,
                chat_id=chat_id,
                author_id=user_id,
            )
            session.add(tr)
            session.commit()

        return True, f"✅ Триггер '{trigger}' успешно добавлен!"

    def remove_trigger(self, user_id: int, chat_id: int, trigger: str, is_admin: bool = False) -> tuple[bool, str]:
        trigger_clean = self._clean_text(trigger)
        with self.session_maker() as session:
            tr = session.scalar(
                select(CustomTrigger).where(
                    CustomTrigger.chat_id == chat_id,
                    CustomTrigger.trigger_word == trigger_clean,
                )
            )

            if not tr:
                return False, "❌ Такой триггер не найден"

            if not is_admin and tr.author_id != user_id:
                return False, "❌ Вы можете удалять только свои триггеры"

            session.delete(tr)
            session.commit()

        return True, f"✅ Триггер '{trigger}' удален"

    def get_chat_triggers(self, chat_id: int) -> dict[str, str]:
        with self.session_maker() as session:
            rows = session.scalars(
                select(CustomTrigger).where(CustomTrigger.chat_id == chat_id)
            ).all()
        return {row.trigger_word: row.response for row in rows}

    def get_trigger_response(self, chat_id: int, trigger: str) -> str | None:
        """Получить ответ на триггер"""
        trigger_clean = self._clean_text(trigger)
        with self.session_maker() as session:
            tr = session.scalar(
                select(CustomTrigger).where(
                    CustomTrigger.chat_id == chat_id,
                    CustomTrigger.trigger_word == trigger_clean,
                )
            )

            if tr:
                tr.uses += 1
                session.commit()
                return tr.response
        return None

    def get_response(self, chat_id: int, text: str) -> Optional[str]:

        """
        Поиск соответствующих триггеров в тексте сообщения
        Проверяет, заканчивается ли сообщение каким-либо триггером

        Args:
            chat_id: ID чата
            text: Текст сообщения

        Returns:
            Ответ на первый найденный триггер или None
        """
        text_clean = self._clean_text(text)

        with self.session_maker() as session:
            triggers = session.scalars(
                select(CustomTrigger).where(CustomTrigger.chat_id == chat_id)
            ).all()

            if not triggers:
                return None

            # сортируем по длине триггера (длинные сначала)
            triggers.sort(key=lambda t: len(t.trigger_word), reverse=True)

            for tr in triggers:
                trig = tr.trigger_word
                if text_clean.endswith(trig):
                    # граница слова: либо точное совпадение, либо перед триггером разделитель
                    boundary_ok = (
                            len(text_clean) == len(trig)
                            or text_clean[-(len(trig) + 1)] in " .,!?;:"
                    )
                    if boundary_ok:
                        tr.uses += 1
                        session.commit()
                        return tr.response

        return None

    def list_chat_triggers(self, chat_id: int) -> str:
        """
        Возвращает человекочитаемый список триггеров чата
        (как в старой версии, с uses)
        """
        with self.session_maker() as session:
            rows = session.scalars(
                select(CustomTrigger).where(CustomTrigger.chat_id == chat_id)
            ).all()

            if not rows:
                return "📝 В этом чате пока нет пользовательских триггеров"

            # Можно отсортировать, например, по алфавиту триггера
            rows.sort(key=lambda r: r.trigger_word)

            result = "📝 **Пользовательские триггеры чата:**\n\n"
            for i, r in enumerate(rows, 1):
                line = f"{i}. '{r.trigger_word}' → '{r.response}'"
                if r.uses > 0:
                    line += f" (использован {r.uses} раз)"
                result += line + "\n"
            return result

    def get_user_stats(self, user_id: int) -> str:
        """
        Считает статистику пользователя БЕЗ отдельной таблицы:
        - total_added: сколько всего создано триггеров (во всех чатах)
        - today_added: сколько создано триггеров сегодня
        - remaining_today: сколько ещё можно сегодня
        """
        today = date.today()

        with self.session_maker() as session:
            total_added = session.scalar(
                select(func.count())
                .select_from(CustomTrigger)
                .where(CustomTrigger.author_id == user_id)
            ) or 0

            today_added = session.scalar(
                select(func.count())
                .select_from(CustomTrigger)
                .where(
                    CustomTrigger.author_id == user_id,
                    CustomTrigger.created == today,
                )
            ) or 0

            remaining_today = max(0, self.MAX_TRIGGERS_PER_USER_PER_DAY - today_added)

            return (
                "📊 **Ваша статистика:**\n\n"
                f"🎯 Всего создано триггеров: {total_added}\n"
                f"📅 Создано сегодня: {today_added}\n"
                f"⏰ Осталось на сегодня: {remaining_today}"
            )
