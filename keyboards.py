# keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
# Импортируем стандартные категории из config
from config import EXPENSE_CATEGORIES as STD_EXPENSE_CATS
from config import INCOME_CATEGORIES as STD_INCOME_CATS
from typing import List # Импортируем List для тайп-хинтов

# --- Основная клавиатура (Reply Keyboard) ---
btn_add_expense = KeyboardButton(text="📊 Записать Расход")
btn_add_income = KeyboardButton(text="💰 Записать Доход")
btn_get_report = KeyboardButton(text="📈 Отчет за месяц")
btn_get_prev_report = KeyboardButton(text="📅 Отчет за прошлый месяц")
btn_get_custom_report = KeyboardButton(text="📊 Отчет за период") # Добавлена кнопка
btn_get_recent = KeyboardButton(text="🕒 Последние записи")
btn_delete_last = KeyboardButton(text="❌ Удалить последнее")
btn_manage_categories = KeyboardButton(text="⚙️ Мои Категории")

# Структура основной клавиатуры (v3 стиль)
main_kb_layout = [
    [btn_add_expense, btn_add_income],               # Строка 1
    [btn_get_report, btn_get_prev_report],           # Строка 2
    [btn_get_custom_report, btn_get_recent],         # Строка 3 (с новой кнопкой)
    [btn_delete_last, btn_manage_categories]         # Строка 4
]
# Создаем объект клавиатуры
main_kb = ReplyKeyboardMarkup(keyboard=main_kb_layout, resize_keyboard=True)


# --- Inline-клавиатура для ВЫБОРА категории ---
async def get_category_choice_kb(user_id: int, category_type: str) -> InlineKeyboardMarkup:
    """
    Создает динамическую inline-клавиатуру для выбора категории.
    Объединяет стандартные и пользовательские категории.

    :param user_id: ID пользователя Telegram.
    :param category_type: Тип категории ('expense' или 'income').
    :return: Объект InlineKeyboardMarkup.
    """
    # Динамический импорт db, чтобы избежать проблем с циклическим импортом
    # если keyboards импортируются в db (хотя в нашем случае это не так)
    import db
    # Получаем пользовательские категории из БД
    user_cats = await db.get_user_categories(user_id, category_type)
    # Получаем стандартные категории из конфига
    standard_cats = STD_EXPENSE_CATS if category_type == 'expense' else STD_INCOME_CATS

    # Объединяем списки через множества для удаления дубликатов,
    # затем преобразуем обратно в список и сортируем.
    all_cats_set = set(standard_cats) | set(user_cats)
    all_cats_sorted = sorted(list(all_cats_set))

    # Используем InlineKeyboardBuilder для удобного создания
    builder = InlineKeyboardBuilder()
    callback_prefix = "exp_cat:" if category_type == 'expense' else "inc_cat:"

    # Добавляем кнопки для каждой категории
    for cat in all_cats_sorted:
        builder.add(InlineKeyboardButton(text=cat, callback_data=f"{callback_prefix}{cat}"))

    # Выстраиваем кнопки в ряды (по 2 в ряд, если их больше 4, иначе в один ряд)
    num_columns = 2 if len(all_cats_sorted) > 4 else 1
    builder.adjust(num_columns)

    # Возвращаем готовую разметку
    return builder.as_markup()

# --- Функции-обертки для совместимости (не обязательно использовать) ---
async def get_expense_categories_kb(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора категории расходов."""
    return await get_category_choice_kb(user_id, 'expense')

async def get_income_categories_kb(user_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру выбора категории доходов."""
    return await get_category_choice_kb(user_id, 'income')


# --- Reply-клавиатура Отмены ---
btn_cancel = KeyboardButton(text="Отмена")
# Структура: одна кнопка в одной строке
cancel_kb_layout = [
    [btn_cancel]
]
# Клавиатура отмены, которая исчезает после нажатия
cancel_kb = ReplyKeyboardMarkup(
    keyboard=cancel_kb_layout,
    resize_keyboard=True,
    one_time_keyboard=True # Удобно для FSM
)


# --- Inline-клавиатуры для УПРАВЛЕНИЯ категориями ---

def get_manage_categories_kb() -> InlineKeyboardMarkup:
    """Возвращает inline-клавиатуру для главного меню управления категориями."""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data="cat_manage:add"))
    builder.row(InlineKeyboardButton(text="➖ Удалить категорию", callback_data="cat_manage:delete"))
    builder.row(InlineKeyboardButton(text="Назад", callback_data="cat_manage:back")) # Кнопка для возврата в основное меню
    return builder.as_markup()

def get_category_type_kb(action_prefix: str) -> InlineKeyboardMarkup:
    """
    Возвращает inline-клавиатуру для выбора типа категории (Доход/Расход).

    :param action_prefix: Префикс для callback_data (например, 'cat_add_type:' или 'cat_del_type:').
    :return: Объект InlineKeyboardMarkup.
    """
    builder = InlineKeyboardBuilder()
    # Две кнопки в ряд для выбора типа
    builder.add(InlineKeyboardButton(text="Расход", callback_data=f"{action_prefix}expense"))
    builder.add(InlineKeyboardButton(text="Доход", callback_data=f"{action_prefix}income"))
    # Кнопка Назад под ними
    builder.row(InlineKeyboardButton(text="<< Назад", callback_data="cat_manage_menu")) # Возврат в меню управления
    return builder.as_markup()

def get_categories_for_delete_kb(categories: List[str]) -> InlineKeyboardMarkup:
    """
    Возвращает inline-клавиатуру со списком пользовательских категорий для удаления.

    :param categories: Список имен категорий для отображения.
    :return: Объект InlineKeyboardMarkup.
    """
    builder = InlineKeyboardBuilder()
    if not categories:
        # Если список пуст, показываем сообщение
        builder.row(InlineKeyboardButton(text="Нет категорий для удаления", callback_data="no_cats_to_delete"))
    else:
        # Для каждой категории создаем кнопку с префиксом 'cat_delete_confirm:'
        for cat in categories:
            builder.row(InlineKeyboardButton(text=f"❌ {cat}", callback_data=f"cat_delete_confirm:{cat}"))
    # Кнопка Назад для возврата к выбору типа категории
    builder.row(InlineKeyboardButton(text="<< Назад", callback_data="cat_delete_choose_type"))
    return builder.as_markup()


# --- Inline-клавиатура для подтверждения УДАЛЕНИЯ ТРАНЗАКЦИИ ---
def get_delete_confirmation_kb(transaction_id: int) -> InlineKeyboardMarkup:
    """
    Возвращает inline-клавиатуру для подтверждения удаления транзакции.

    :param transaction_id: ID транзакции, которая будет удалена.
    :return: Объект InlineKeyboardMarkup.
    """
    builder = InlineKeyboardBuilder()
    # Две кнопки в ряд: Да и Отмена
    builder.add(InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"delete_confirm:{transaction_id}"))
    builder.add(InlineKeyboardButton(text="🚫 Отмена", callback_data="delete_cancel"))
    # Выстраивать в один ряд не нужно, т.к. builder.add по умолчанию добавляет в текущий ряд
    return builder.as_markup()