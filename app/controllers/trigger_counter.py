class TriggerCounter:
    def __init__(self):
        # Теперь считаем по чатам, а не по пользователям
        self.chat_trigger_counts = {}

    def increment_chat_trigger_count(self, chat_id: int) -> int:
        """Увеличить общий счетчик триггеров для чата"""
        self.chat_trigger_counts[chat_id] = self.chat_trigger_counts.get(chat_id, 0) + 1
        return self.chat_trigger_counts[chat_id]

    def reset_chat_trigger_count(self, chat_id: int):
        """Сбросить счетчик триггеров для чата (после показа NPS опроса)"""
        self.chat_trigger_counts[chat_id] = 0
        print(f"🔄 Счетчик триггеров для чата {chat_id} сброшен")

    def get_chat_trigger_count(self, chat_id: int) -> int:
        """Получить текущий счетчик триггеров для чата"""
        return self.chat_trigger_counts.get(chat_id, 0)

# Глобальный экземпляр
trigger_counter = TriggerCounter()
