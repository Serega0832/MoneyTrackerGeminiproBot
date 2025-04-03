# handlers/reports.py
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
# --- ДОБАВИТЬ ИМПОРТ ---
from aiogram.utils.markdown import hbold, hitalic
import keyboards as kb
import db

reports_router = Router()

MONTH_NAMES_RU = {
    1: "Январь", 2: "Февраль", 3: "Март", 4: "Апрель", 5: "Май", 6: "Июнь",
    7: "Июль", 8: "Август", 9: "Сентябрь", 10: "Октябрь", 11: "Ноябрь", 12: "Декабрь"
}

def format_report_text(period_name: str, income: float, expense: float, details: dict[str, float]) -> str:
    # Здесь hbold не используется, форматирование уже применено при вызове
    balance = income - expense
    report_text = f"📊 <b>Отчет за {period_name}:</b>\n\n" \
                  f"🟢 Доходы: {income:.2f}\n" \
                  f"🔴 Расходы: {expense:.2f}\n\n" \
                  f"💰 Баланс: {balance:.2f}\n"
    if details:
        report_text += "\n📈 <b>Расходы по категориям:</b>\n"
        sorted_details = sorted(details.items(), key=lambda item: item[1], reverse=True)
        for category, amount in sorted_details:
            report_text += f" - {category}: {amount:.2f}\n"
    elif expense > 0: report_text += "\n📈 Детализация расходов недоступна."
    else: report_text += "\n📈 Расходов в этом периоде не было."
    return report_text

@reports_router.message(F.text == "📈 Отчет за месяц", StateFilter(None))
@reports_router.message(Command("report"), StateFilter(None))
async def process_get_current_month_report(message: types.Message, state: FSMContext):
    await state.clear(); user_id = message.from_user.id; logging.info(f"Отчет тек. месяц от {user_id}")
    now = datetime.now(timezone.utc); start_of_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    if now.month == 12: end_of_month = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
    else: end_of_month = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)
    month_number = start_of_month.month; month_name_str = MONTH_NAMES_RU.get(month_number, f"{month_number:02d}"); year_str = start_of_month.year
    report_period_name = f"тек. месяц ({month_name_str} {year_str})"
    income, expense, details = await db.get_period_summary_with_details(user_id, start_of_month, end_of_month)
    report_text = format_report_text(report_period_name, income, expense, details); await message.answer(report_text, reply_markup=kb.main_kb)

@reports_router.message(F.text == "📅 Отчет за прошлый месяц", StateFilter(None))
@reports_router.message(Command("prevmonthreport"), StateFilter(None))
async def process_get_previous_month_report(message: types.Message, state: FSMContext):
    await state.clear(); user_id = message.from_user.id; logging.info(f"Отчет пред. месяц от {user_id}")
    now = datetime.now(timezone.utc); end_of_previous_month = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    start_of_previous_month = datetime((end_of_previous_month - timedelta(days=1)).year, (end_of_previous_month - timedelta(days=1)).month, 1, tzinfo=timezone.utc)
    month_number = start_of_previous_month.month; month_name_str = MONTH_NAMES_RU.get(month_number, f"{month_number:02d}"); year_str = start_of_previous_month.year
    report_period_name = f"прошлый месяц ({month_name_str} {year_str})"
    income, expense, details = await db.get_period_summary_with_details(user_id, start_of_previous_month, end_of_previous_month)
    report_text = format_report_text(report_period_name, income, expense, details); await message.answer(report_text, reply_markup=kb.main_kb)

@reports_router.message(F.text == "🕒 Последние записи", StateFilter(None))
@reports_router.message(Command("recent"), StateFilter(None))
async def process_get_recent(message: types.Message, state: FSMContext):
    await state.clear(); user_id = message.from_user.id; logging.info(f"Последние записи от {user_id}")
    transactions = await db.get_recent_transactions(user_id, limit=10)
    if not transactions: await message.answer("Нет записей.", reply_markup=kb.main_kb); return
    response_lines = ["🕒 <b>Последние 10 записей:</b>\n"]
    for row in transactions:
        try: dt_obj = datetime.fromisoformat(row['created_at']) if isinstance(row['created_at'], str) else row['created_at']; dt_str = dt_obj.strftime("%d.%m.%Y %H:%M")
        except: dt_str = str(row['created_at'])
        symbol = "🟢" if row['transaction_type'] == 'income' else "🔴"
        # Используем импортированный hitalic
        line = f"{dt_str} {symbol} {row['amount']:.2f} - {hitalic(row['category'])}"
        response_lines.append(line)
    await message.answer("\n".join(response_lines), reply_markup=kb.main_kb)