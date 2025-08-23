"""
Модуль для управления настройками чата
Позволяет отключать/включать бота и настраивать вероятность ответов
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import random


class ChatSettingsManager:
    def __init__(self, settings_file: str = "chat_settings.json"):
        """
        Инициализация менеджера настроек чата

        Args:
            settings_file (str): Путь к файлу с настройками
        """
        self.settings_file = settings_file
        self.data = self._load_settings()

    def _load_settings(self) -> Dict[str, Any]:
        """Загрузка настроек из файла"""
        if not os.path.exists(self.settings_file):
            return {
                "chats": {},  # Настройки по чатам
                "version": "1.0"
            }

        try:
            with open(self.settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return self._load_settings()  # Возвращаем пустую структуру при ошибке

    def _save_settings(self):
        """Сохранение настроек в файл"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения настроек чата: {e}")

    def _get_chat_settings(self, chat_id: int) -> Dict[str, Any]:
        """Получить настройки чата"""
        chat_str = str(chat_id)

        if chat_str not in self.data["chats"]:
            # Настройки по умолчанию
            default_settings = {
                "enabled": True,  # Бот включен по умолчанию
                "response_chance": 100,  # 100% вероятность ответа
                "last_modified": datetime.now().isoformat(),
                "modified_by": None
            }
            self.data["chats"][chat_str] = default_settings
            self._save_settings()

        return self.data["chats"][chat_str]

    def is_bot_enabled(self, chat_id: int) -> bool:
        """Проверить, включен ли бот в чате"""
        settings = self._get_chat_settings(chat_id)
        return settings.get("enabled", True)

    def set_bot_enabled(self, chat_id: int, enabled: bool, user_id: int) -> tuple[
        bool, str]:
        """
        Включить/выключить бота в чате

        Args:
            chat_id: ID чата
            enabled: True - включить, False - выключить
            user_id: ID пользователя, который изменил настройку

        Returns:
            tuple: (успешно ли, сообщение)
        """
        chat_str = str(chat_id)
        settings = self._get_chat_settings(chat_id)

        settings["enabled"] = enabled
        settings["last_modified"] = datetime.now().isoformat()
        settings["modified_by"] = user_id

        self.data["chats"][chat_str] = settings
        self._save_settings()

        status = "включен" if enabled else "выключен"
        emoji = "✅" if enabled else "❌"

        return True, f"{emoji} Бот {status} в этом чате!"

    def get_response_chance(self, chat_id: int) -> int:
        """Получить вероятность ответа для чата"""
        settings = self._get_chat_settings(chat_id)
        return settings.get("response_chance", 100)

    def set_response_chance(self, chat_id: int, chance: int, user_id: int) -> tuple[
        bool, str]:
        """
        Установить вероятность ответа бота

        Args:
            chat_id: ID чата
            chance: Вероятность от 0 до 100
            user_id: ID пользователя, который изменил настройку

        Returns:
            tuple: (успешно ли, сообщение)
        """
        if not (0 <= chance <= 100):
            return False, "❌ Вероятность должна быть от 0 до 100!"

        chat_str = str(chat_id)
        settings = self._get_chat_settings(chat_id)

        settings["response_chance"] = chance
        settings["last_modified"] = datetime.now().isoformat()
        settings["modified_by"] = user_id

        self.data["chats"][chat_str] = settings
        self._save_settings()

        return True, f"🎯 Вероятность ответа установлена: {chance}%"

    def should_respond(self, chat_id: int) -> bool:
        """
        Определить, должен ли бот отвечать на сообщение
        Проверяет и включен ли бот, и вероятность ответа

        Args:
            chat_id: ID чата

        Returns:
            bool: True если бот должен ответить
        """
        # Если бот выключен, не отвечаем
        if not self.is_bot_enabled(chat_id):
            return False

        # Проверяем вероятность
        chance = self.get_response_chance(chat_id)
        if chance == 0:
            return False
        if chance == 100:
            return True

        # Генерируем случайное число от 1 до 100
        return random.randint(1, 100) <= chance

    def get_chat_info(self, chat_id: int) -> str:
        """Получить информацию о настройках чата"""
        settings = self._get_chat_settings(chat_id)

        enabled = settings.get("enabled", True)
        chance = settings.get("response_chance", 100)
        last_modified = settings.get("last_modified", "Никогда")

        status_emoji = "✅" if enabled else "❌"
        status_text = "включен" if enabled else "выключен"

        if last_modified != "Никогда":
            # Форматируем дату
            try:
                date_obj = datetime.fromisoformat(last_modified)
                last_modified = date_obj.strftime("%d.%m.%Y %H:%M")
            except:
                pass

        info_text = f"""⚙️ **Настройки бота в чате:**

{status_emoji} Статус: {status_text}
🎯 Вероятность ответа: {chance}%
📅 Последнее изменение: {last_modified}"""

        return info_text

    def reset_chat_settings(self, chat_id: int, user_id: int) -> tuple[bool, str]:
        """Сбросить настройки чата к значениям по умолчанию"""
        chat_str = str(chat_id)

        default_settings = {
            "enabled": True,
            "response_chance": 100,
            "last_modified": datetime.now().isoformat(),
            "modified_by": user_id
        }

        self.data["chats"][chat_str] = default_settings
        self._save_settings()

        return True, "🔄 Настройки чата сброшены к значениям по умолчанию!"


# Создаем глобальный экземпляр менеджера настроек
chat_settings_manager = ChatSettingsManager()