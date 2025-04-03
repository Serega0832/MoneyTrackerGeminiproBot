# states.py
from aiogram.fsm.state import State, StatesGroup

class TransactionStates(StatesGroup):
    """Состояния для добавления транзакции"""
    waiting_for_amount = State()
    waiting_for_category = State()

class CategoryManagementStates(StatesGroup):
    """Состояния для добавления/удаления категорий"""
    choosing_action = State()
    choosing_type_to_add = State()
    waiting_for_name_to_add = State()
    choosing_type_to_delete = State()
    choosing_category_to_delete = State()

# --- НОВОЕ: Состояния для отчета за произвольный период ---
class CustomReportStates(StatesGroup):
    """Состояния для запроса дат для отчета"""
    waiting_for_start_date = State()
    waiting_for_end_date = State()