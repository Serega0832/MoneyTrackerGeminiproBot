# handlers/custom_report.py
import logging
from datetime import datetime, timezone, timedelta # Добавил timedelta
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
# --- ДОБАВИТЬ ИМПОРТ ---
from aiogram.utils.markdown import hbold
import keyboards as kb
import db
from states import CustomReportStates
# Импортируем форматирование из reports.py (или можно вынести в отдельный utils.py)
from .reports import format_report_text

custom_report_router = Router()

DATE_FORMAT = "%d.%m.%Y"

@custom_report_router.message(Command("customreport"), StateFilter(None))
# @custom_report_router.message(F.text == "📊 Отчет за период", StateFilter(None)) # Раскомментировать, когда добавим кнопку
async def cmd_custom_report(message: types.Message, state: FSMContext):
    await state.set_state(CustomReportStates.waiting_for_start_date)
    # Используем импортированный hbold
    await message.answer(
        f"Введите дату начала периода в формате {hbold(DATE_FORMAT)} (например, 01.01.2024):",
        reply_markup=kb.cancel_kb
    )

@custom_report_router.message(StateFilter(CustomReportStates.waiting_for_start_date))
async def process_start_date(message: types.Message, state: FSMContext):
    try:
        start_date_naive = datetime.strptime(message.text, DATE_FORMAT)
        start_date = start_date_naive.replace(tzinfo=timezone.utc)
        await state.update_data(start_date=start_date)
        await state.set_state(CustomReportStates.waiting_for_end_date)
        # Используем импортированный hbold
        await message.answer(
            f"Отлично! Теперь введите дату конца периода в формате {hbold(DATE_FORMAT)}:",
            reply_markup=kb.cancel_kb
        )
    except ValueError:
        # Используем импортированный hbold
        await message.answer(
            f"Неверный формат даты. Введите {hbold(DATE_FORMAT)} или 'Отмена'."
        )

@custom_report_router.message(StateFilter(CustomReportStates.waiting_for_end_date))
async def process_end_date(message: types.Message, state: FSMContext):
    try:
        end_date_naive = datetime.strptime(message.text, DATE_FORMAT)
        end_date = (end_date_naive + timedelta(days=1)).replace(tzinfo=timezone.utc)
        user_data = await state.get_data()
        start_date = user_data.get('start_date')

        if end_date <= start_date:
            await message.answer("Дата конца не может быть раньше даты начала.", reply_markup=kb.cancel_kb); return

        user_id = message.from_user.id
        logging.info(f"Отчет за период {start_date.strftime(DATE_FORMAT)} - {end_date_naive.strftime(DATE_FORMAT)} от {user_id}")
        income, expense, details = await db.get_period_summary_with_details(user_id, start_date, end_date)
        period_name = f"период с {start_date.strftime(DATE_FORMAT)} по {end_date_naive.strftime(DATE_FORMAT)}"
        report_text = format_report_text(period_name, income, expense, details)
        await message.answer(report_text, reply_markup=kb.main_kb)
        await state.clear()

    except ValueError:
         # Используем импортированный hbold
        await message.answer(f"Неверный формат даты. Введите {hbold(DATE_FORMAT)} или 'Отмена'.")
    except Exception as e:
        logging.error(f"Ошибка при формировании отчета за период: {e}")
        await message.answer("Ошибка при формировании отчета.", reply_markup=kb.main_kb)
        await state.clear()