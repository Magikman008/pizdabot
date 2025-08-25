"""
Модуль для управления пользовательскими триггерами
Позволяет участникам добавлять локальные триггеры для каждого чата
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, Any, Optional


class UserTriggerManager:
    def __init__(self, triggers_file: str = "user_triggers.json"):
        """
        Инициализация менеджера пользовательских триггеров

        Args:
            triggers_file (str): Путь к файлу с триггерами
        """
        self.triggers_file = triggers_file
        self.data = self._load_triggers()

        # Настройки модерации
        self.MAX_TRIGGERS_PER_USER_PER_DAY = 3
        self.MAX_TRIGGERS_PER_CHAT = 50
        self.MIN_TRIGGER_LENGTH = 2
        self.MIN_RESPONSE_LENGTH = 1
        self.MAX_TRIGGER_LENGTH = 100
        self.MAX_RESPONSE_LENGTH = 500

    def _load_triggers(self) -> Dict[str, Any]:
        """Загрузка пользовательских триггеров из файла"""
        if not os.path.exists(self.triggers_file):
            return {
                "chat_triggers": {},  # Триггеры по чатам
                "user_stats": {},  # Статистика пользователей
                "version": "1.0",
            }

        try:
            with open(self.triggers_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._load_triggers()  # Возвращаем пустую структуру при ошибке

    def _save_triggers(self):
        """Сохранение триггеров в файл"""
        try:
            with open(self.triggers_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения пользовательских триггеров: {e}")

    def _clean_text(self, text: str) -> str:
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
        Проверяет, может ли пользователь добавить триггер

        Returns:
            tuple: (можно ли добавить, сообщение об ошибке)
        """
        chat_str = str(chat_id)
        user_str = str(user_id)

        # Проверяем лимит триггеров в чате
        if chat_str in self.data["chat_triggers"]:
            if len(self.data["chat_triggers"][chat_str]) >= self.MAX_TRIGGERS_PER_CHAT:
                return (
                    False,
                    f"❌ В чате уже максимальное количество триггеров ({self.MAX_TRIGGERS_PER_CHAT})",
                )

        # Проверяем дневной лимит пользователя
        today = datetime.now().strftime("%Y-%m-%d")
        if user_str not in self.data["user_stats"]:
            self.data["user_stats"][user_str] = {}

        user_stats = self.data["user_stats"][user_str]
        today_count = user_stats.get(f"added_{today}", 0)

        if today_count >= self.MAX_TRIGGERS_PER_USER_PER_DAY:
            return (
                False,
                f"❌ Вы уже добавили максимальное количество триггеров на сегодня ({self.MAX_TRIGGERS_PER_USER_PER_DAY})",
            )

        return True, ""

    def add_trigger(
        self, user_id: int, chat_id: int, trigger: str, response: str
    ) -> tuple[bool, str]:
        """
        Добавляет пользовательский триггер

        Returns:
            tuple: (успешно ли, сообщение)
        """
        # Валидация
        error = self._validate_trigger(trigger, response)
        if error:
            return False, error

        # Проверяем права пользователя
        can_add, error_msg = self.can_user_add_trigger(user_id, chat_id)
        if not can_add:
            return False, error_msg

        chat_str = str(chat_id)
        user_str = str(user_id)
        trigger_clean = self._clean_text(trigger)

        # Инициализируем структуру для чата если нужно
        if chat_str not in self.data["chat_triggers"]:
            self.data["chat_triggers"][chat_str] = {}

        # Проверяем на дублирование
        if trigger_clean in self.data["chat_triggers"][chat_str]:
            return False, "❌ Такой триггер уже существует в этом чате"

        # Добавляем триггер
        self.data["chat_triggers"][chat_str][trigger_clean] = {
            "response": response,
            "author": user_id,
            "created": datetime.now().isoformat(),
            "uses": 0,
        }

        # Обновляем статистику пользователя
        today = datetime.now().strftime("%Y-%m-%d")
        if user_str not in self.data["user_stats"]:
            self.data["user_stats"][user_str] = {}

        self.data["user_stats"][user_str][f"added_{today}"] = (
            self.data["user_stats"][user_str].get(f"added_{today}", 0) + 1
        )
        self.data["user_stats"][user_str]["total_added"] = (
            self.data["user_stats"][user_str].get("total_added", 0) + 1
        )

        self._save_triggers()
        return True, f"✅ Триггер '{trigger}' успешно добавлен!"

    def remove_trigger(
        self, user_id: int, chat_id: int, trigger: str, is_admin: bool = False
    ) -> tuple[bool, str]:
        """
        Удаляет пользовательский триггер

        Args:
            is_admin: Может ли пользователь удалять чужие триггеры
        """
        chat_str = str(chat_id)
        trigger_clean = self._clean_text(trigger)

        if chat_str not in self.data["chat_triggers"]:
            return False, "❌ В этом чате нет пользовательских триггеров"

        if trigger_clean not in self.data["chat_triggers"][chat_str]:
            return False, "❌ Такой триггер не найден"

        trigger_data = self.data["chat_triggers"][chat_str][trigger_clean]

        # Проверяем права на удаление
        if not is_admin and trigger_data["author"] != user_id:
            return False, "❌ Вы можете удалять только свои триггеры"

        # Удаляем триггер
        del self.data["chat_triggers"][chat_str][trigger_clean]

        # Очищаем пустые чаты
        if not self.data["chat_triggers"][chat_str]:
            del self.data["chat_triggers"][chat_str]

        self._save_triggers()
        return True, f"✅ Триггер '{trigger}' удален"

    def get_chat_triggers(self, chat_id: int) -> Dict[str, str]:
        """Получить все триггеры для чата"""
        chat_str = str(chat_id)
        if chat_str not in self.data["chat_triggers"]:
            return {}

        # Возвращаем только триггер -> ответ (убираем метаданные)
        return {
            trigger: data["response"]
            for trigger, data in self.data["chat_triggers"][chat_str].items()
        }

    def get_trigger_response(self, chat_id: int, trigger: str) -> Optional[str]:
        """Получить ответ на триггер"""
        chat_str = str(chat_id)
        trigger_clean = self._clean_text(trigger)

        if (
            chat_str in self.data["chat_triggers"]
            and trigger_clean in self.data["chat_triggers"][chat_str]
        ):

            # Увеличиваем счетчик использований
            self.data["chat_triggers"][chat_str][trigger_clean]["uses"] += 1
            self._save_triggers()

            return self.data["chat_triggers"][chat_str][trigger_clean]["response"]

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
        chat_str = str(chat_id)

        if chat_str not in self.data["chat_triggers"]:
            return None

        text_clean = self._clean_text(text)

        # Проверяем все триггеры, сортируя по длине (сначала длинные)
        triggers = sorted(
            self.data["chat_triggers"][chat_str].items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )

        for trigger, trigger_data in triggers:
            # Проверяем, заканчивается ли сообщение этим триггером
            if text_clean.endswith(trigger):
                # Дополнительная проверка: триггер должен быть отдельным словом
                if (
                    len(text_clean) == len(trigger)
                    or text_clean[-(len(trigger) + 1)] in " .,!?;:"
                ):
                    # Увеличиваем счетчик использований
                    self.data["chat_triggers"][chat_str][trigger]["uses"] += 1
                    self._save_triggers()
                    return trigger_data["response"]

        return None

    def list_chat_triggers(self, chat_id: int) -> str:
        """Получить список триггеров чата в виде текста"""
        chat_str = str(chat_id)

        if chat_str not in self.data["chat_triggers"]:
            return "📝 В этом чате пока нет пользовательских триггеров"

        triggers = self.data["chat_triggers"][chat_str]
        if not triggers:
            return "📝 В этом чате пока нет пользовательских триггеров"

        result = "📝 **Пользовательские триггеры чата:**\n\n"

        for i, (trigger, data) in enumerate(triggers.items(), 1):
            uses = data.get("uses", 0)
            result += f"{i}. '{trigger}' → '{data['response']}'"
            if uses > 0:
                result += f" (использован {uses} раз)"
            result += "\n"

        return result

    def get_user_stats(self, user_id: int) -> str:
        """Получить статистику пользователя"""
        user_str = str(user_id)

        if user_str not in self.data["user_stats"]:
            return "📊 У вас пока нет статистики по триггерам"

        stats = self.data["user_stats"][user_str]
        total_added = stats.get("total_added", 0)
        today = datetime.now().strftime("%Y-%m-%d")
        today_added = stats.get(f"added_{today}", 0)

        remaining_today = max(0, self.MAX_TRIGGERS_PER_USER_PER_DAY - today_added)

        return f"""📊 **Ваша статистика:**

🎯 Всего создано триггеров: {total_added}
📅 Создано сегодня: {today_added}
⏰ Осталось на сегодня: {remaining_today}"""
