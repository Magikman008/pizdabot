from aiogram.fsm.state import State, StatesGroup

class FeedbackStates(StatesGroup):
    """
    Состояния для процесса отправки обратной связи
    Полностью переписанная реализация с дополнительными состояниями
    """
    # Основные состояния для пользователей
    waiting_for_message = State()
    confirming_send = State()