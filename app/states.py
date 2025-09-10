"""
Состояния для машины состояний (FSM) бота
"""
from aiogram.fsm.state import State, StatesGroup

class FeedbackStates(StatesGroup):
    """Состояния для процесса отправки обратной связи"""
    waiting_for_message = State()  # Ожидание сообщения от пользователя
    confirming_send = State()      # Подтверждение отправки
