"""
Модуль для работы со статистикой бота
Отслеживает количество подъёбов, пользователей и групп
"""

import json
import os
from datetime import datetime
from typing import Dict, Any


class BotStatistics:
    def __init__(self, stats_file: str = "bot_stats.json"):
        """
        Инициализация класса статистики

        Args:
            stats_file (str): Путь к файлу статистики
        """
        self.stats_file = stats_file
        self.stats = self._load_stats()

    def _load_stats(self) -> Dict[str, Any]:
        """Загрузка статистики из файла"""
        if not os.path.exists(self.stats_file):
            return {
                "total_roasts": 0,
                "unique_users": set(),
                "unique_groups": set(),
                "daily_stats": {},
                "trigger_stats": {},
                "start_date": datetime.now().isoformat(),
            }

        try:
            with open(self.stats_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            # top-level множества
            data["unique_users"] = set(data.get("unique_users", []))
            data["unique_groups"] = set(data.get("unique_groups", []))
            # Конвертируем вложенные списки daily_stats → множества
            for date, day in data.get("daily_stats", {}).items():
                if isinstance(day.get("users"), list):
                    day["users"] = set(day["users"])
                if isinstance(day.get("groups"), list):
                    day["groups"] = set(day["groups"])
            return data

        except (json.JSONDecodeError, FileNotFoundError):
            # при ошибке возвращаем новую пустую статистику
            return {
                "total_roasts": 0,
                "unique_users": set(),
                "unique_groups": set(),
                "daily_stats": {},
                "trigger_stats": {},
                "start_date": datetime.now().isoformat(),
            }

    def _save_stats(self):
        """Сохранение статистики в файл"""
        # Преобразуем множества в списки для JSON сериализации
        data_to_save = self.stats.copy()
        data_to_save["unique_users"] = list(self.stats["unique_users"])
        data_to_save["unique_groups"] = list(self.stats["unique_groups"])

        # Преобразуем множества в дневной статистике
        daily_stats_copy = {}
        for date, day_data in self.stats["daily_stats"].items():
            daily_stats_copy[date] = day_data.copy()
            if isinstance(day_data.get("users"), set):
                daily_stats_copy[date]["users"] = list(day_data["users"])
            if isinstance(day_data.get("groups"), set):
                daily_stats_copy[date]["groups"] = list(day_data["groups"])
        data_to_save["daily_stats"] = daily_stats_copy

        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения статистики: {e}")

    def add_roast(self, user_id: int, chat_id: int, trigger: str):
        """
        Добавить запись о подъёбе

        Args:
            user_id (int): ID пользователя
            chat_id (int): ID чата
            trigger (str): Сработавший триггер
        """
        # Увеличиваем общий счётчик
        self.stats["total_roasts"] += 1

        # Добавляем пользователя
        self.stats["unique_users"].add(user_id)

        # Добавляем группу (если это не приватный чат)
        if chat_id != user_id:  # В приватном чате chat_id == user_id
            self.stats["unique_groups"].add(chat_id)

        # Статистика по дням
        today = datetime.now().strftime("%Y-%m-%d")
        if today not in self.stats["daily_stats"]:
            self.stats["daily_stats"][today] = {
                "roasts": 0,
                "users": set(),
                "groups": set(),
            }

        self.stats["daily_stats"][today]["roasts"] += 1
        self.stats["daily_stats"][today]["users"].add(user_id)
        if chat_id != user_id:
            self.stats["daily_stats"][today]["groups"].add(chat_id)

        # Статистика по триггерам
        if trigger not in self.stats["trigger_stats"]:
            self.stats["trigger_stats"][trigger] = 0
        self.stats["trigger_stats"][trigger] += 1

        # Сохраняем статистику
        self._save_stats()

    def get_total_stats(self) -> Dict[str, Any]:
        """Получить общую статистику"""
        return {
            "total_roasts": self.stats["total_roasts"],
            "unique_users": len(self.stats["unique_users"]),
            "unique_groups": len(self.stats["unique_groups"]),
            "days_active": len(self.stats["daily_stats"]),
            "start_date": self.stats["start_date"],
        }

    def get_top_triggers(self, limit: int = 10) -> Dict[str, int]:
        """Получить топ триггеров"""
        trigger_stats = self.stats.get("trigger_stats", {})
        sorted_triggers = sorted(
            trigger_stats.items(), key=lambda x: x[1], reverse=True
        )
        return dict(sorted_triggers[:limit])

    def get_daily_stats(self, date: str = None) -> Dict[str, Any]:
        """
        Получить статистику за день

        Args:
            date (str): Дата в формате YYYY-MM-DD (если None, то сегодня)
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        daily_data = self.stats["daily_stats"].get(
            date, {"roasts": 0, "users": set(), "groups": set()}
        )

        return {
            "date": date,
            "roasts": daily_data.get("roasts", 0),
            "unique_users": len(daily_data.get("users", set())),
            "unique_groups": len(daily_data.get("groups", set())),
        }

    def get_stats_summary(self) -> str:
        """Получить текстовое резюме статистики"""
        total = self.get_total_stats()
        today = self.get_daily_stats()
        top_triggers = self.get_top_triggers(5)

        summary = f"""📊 Статистика бота

🔥 Всего подъёбов: {total['total_roasts']}
👥 Уникальных пользователей: {total['unique_users']}
💬 Уникальных групп: {total['unique_groups']}
📅 Дней активности: {total['days_active']}

Сегодня ({today['date']}):
🔥 Подъёбов: {today['roasts']}
👥 Пользователей: {today['unique_users']}
💬 Групп: {today['unique_groups']}

Топ триггеров:"""

        for i, (trigger, count) in enumerate(top_triggers.items(), 1):
            summary += f"\n{i}. '{trigger}' - {count} раз"

        return summary

    def get_detailed_stats(self) -> str:
        """Получить детальную статистику для админов"""
        total = self.get_total_stats()
        today = self.get_daily_stats()
        top_triggers = self.get_top_triggers(10)

        # Последние 7 дней
        weekly_stats = []
        for i in range(7):
            from datetime import timedelta

            date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            day_stats = self.get_daily_stats(date)
            weekly_stats.append(day_stats)

        detailed = f"""📊 Детальная статистика бота

🔥 Всего подъёбов: {total['total_roasts']}
👥 Уникальных пользователей: {total['unique_users']}
💬 Уникальных групп: {total['unique_groups']}
📅 Дней активности: {total['days_active']}
🚀 Запущен: {total['start_date'][:10]}

Активность за последние 7 дней:"""

        for day in weekly_stats:
            detailed += f"\n{day['date']}: {day['roasts']} подъёбов"

        detailed += "\n\nТоп-10 триггеров:"
        for i, (trigger, count) in enumerate(top_triggers.items(), 1):
            detailed += f"\n{i}. '{trigger}' - {count} раз"

        return detailed

    def clear_stats(self):
        """Очистить статистику"""
        self.stats = {
            "total_roasts": 0,
            "unique_users": set(),
            "unique_groups": set(),
            "daily_stats": {},
            "trigger_stats": {},
            "start_date": datetime.now().isoformat(),
        }
        self._save_stats()

    def export_stats(self) -> dict:
        """Экспорт статистики в формате для JSON"""
        data_to_export = self.stats.copy()
        data_to_export["unique_users"] = list(self.stats["unique_users"])
        data_to_export["unique_groups"] = list(self.stats["unique_groups"])

        # Преобразуем дневную статистику
        daily_stats_export = {}
        for date, day_data in self.stats["daily_stats"].items():
            daily_stats_export[date] = {
                "roasts": day_data.get("roasts", 0),
                "users": list(day_data.get("users", set())),
                "groups": list(day_data.get("groups", set())),
            }
        data_to_export["daily_stats"] = daily_stats_export

        return data_to_export


# Создаем глобальный экземпляр статистики
bot_stats = BotStatistics()
