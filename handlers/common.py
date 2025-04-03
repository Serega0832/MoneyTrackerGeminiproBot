# handlers/common.py
import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
import keyboards as kb # Импортируем клавиатуры

common_router = Router() # Создаем роутер для общих команд

@common_router.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    """Обработчик команды /start."""
    await state.clear() # Сбрасываем состояние на всякий случай
    user_name = message.from_user.first_name
    await message.answer(f"Привет, {user_name}!\n"
                         f"Я бот для учета твоих финансов.\n\n"
                         f"Используй кнопки ниже.",
                         reply_markup=kb.main_kb) # Показываем главную клавиатуру

@common_router.message(Command("help"))
async def send_help(message: types.Message):
    """Обработчик команды /help."""
    # Можно добавить более подробный текст справки
    help_text = (
        "Я помогу тебе следить за доходами и расходами.\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать работу / Сбросить состояние\n"
        "/mycategories - Управление категориями\n"
        "/report - Отчет за текущий месяц\n"
        "/prevmonthreport - Отчет за прошлый месяц\n"
        "/recent - Показать последние записи\n"
        "/deletelast - Удалить последнюю запись\n"
        "/cancel - Отменить текущее действие\n"
        "/help - Показать эту справку\n\n"
        "Используй кнопки внизу для быстрого доступа."
    )
    await message.answer(help_text, reply_markup=kb.main_kb)


@common_router.message(Command("cancel"), StateFilter('*'))
@common_router.message(F.text.lower() == 'отмена', StateFilter('*'))
async def cancel_handler(message: types.Message, state: FSMContext):
    """Обработчик отмены действия."""
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Нет активных действий для отмены.", reply_markup=kb.main_kb)
        return
    logging.info(f'Cancelling state {current_state} for user {message.from_user.id}')
    await state.clear()
    await message.answer('Действие отменено.', reply_markup=kb.main_kb)