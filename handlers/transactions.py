# handlers/transactions.py
import logging
from aiogram import Router, types, F, Bot # Добавил Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
# --- ДОБАВИТЬ ИМПОРТ ---
from aiogram.utils.markdown import hbold
import keyboards as kb
import db
from states import TransactionStates

transactions_router = Router()

# --- Обработчики Добавления Транзакций ---
# ... (process_add_expense, process_add_income, process_amount - без hbold) ...
@transactions_router.message(F.text == "📊 Записать Расход", StateFilter(None))
async def process_add_expense(message: types.Message, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_amount); await state.update_data(transaction_type='expense')
    await message.answer("Введите сумму расхода:", reply_markup=kb.cancel_kb)
@transactions_router.message(F.text == "💰 Записать Доход", StateFilter(None))
async def process_add_income(message: types.Message, state: FSMContext):
    await state.set_state(TransactionStates.waiting_for_amount); await state.update_data(transaction_type='income')
    await message.answer("Введите сумму дохода:", reply_markup=kb.cancel_kb)
@transactions_router.message(StateFilter(TransactionStates.waiting_for_amount))
async def process_amount(message: types.Message, state: FSMContext):
    try: amount_str = message.text.replace(',', '.'); amount = float(amount_str); assert amount > 0
    except (ValueError, AssertionError): await message.answer("Введите корректную сумму (> 0)."); return
    await state.update_data(amount=amount); user_data = await state.get_data(); transaction_type = user_data.get('transaction_type')
    await state.set_state(TransactionStates.waiting_for_category); user_id = message.from_user.id
    try: reply_markup = await kb.get_category_choice_kb(user_id, transaction_type)
    except Exception as e: logging.error(f"Ошибка клавы категорий {user_id}, {transaction_type}: {e}"); await message.answer("Ошибка загрузки клавы.", reply_markup=kb.cancel_kb); return
    prompt_text = "Категория расхода:" if transaction_type == 'expense' else "Категория дохода:"
    if not reply_markup or not reply_markup.inline_keyboard: logging.warning(f"Клава категорий пуста {user_id}, {transaction_type}."); await message.answer("Нет категорий. Добавьте в 'Мои Категории'.", reply_markup=kb.main_kb); await state.clear(); return
    await message.answer(prompt_text, reply_markup=reply_markup)


@transactions_router.callback_query(StateFilter(TransactionStates.waiting_for_category), F.data.startswith('exp_cat:') | F.data.startswith('inc_cat:'))
async def process_category_callback(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot): # Добавил bot
    current_state = await state.get_state()
    if current_state != TransactionStates.waiting_for_category.state: await callback_query.answer("Начните заново.", show_alert=True); return
    code = callback_query.data
    try: prefix, category = code.split(':', 1)
    except ValueError: logging.warning(f"Некорр. cb '{code}' от {callback_query.from_user.id}"); await callback_query.answer("Ошибка.", show_alert=True); return
    user_data = await state.get_data(); amount = user_data.get('amount'); transaction_type = user_data.get('transaction_type')
    if (prefix == 'exp_cat' and transaction_type != 'expense') or (prefix == 'inc_cat' and transaction_type != 'income'): await callback_query.answer("Ошибка типа.", show_alert=True); return
    try: await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
    except Exception as e: logging.error(f"Не уд. убрать клаву: {e}")
    success = await db.add_transaction(user_id=callback_query.from_user.id, transaction_type=transaction_type, amount=amount, category=category)
    if success:
        type_text = "Расход" if transaction_type == 'expense' else "Доход"
        # Используем импортированный hbold
        await callback_query.message.answer(f"{type_text} на сумму {hbold(f'{amount:.2f}')} в категории {hbold(category)} успешно записан!", reply_markup=kb.main_kb)
    else:
        await callback_query.message.answer("Не удалось сохранить запись.", reply_markup=kb.main_kb)
    await callback_query.answer(); await state.clear()

@transactions_router.message(StateFilter(TransactionStates.waiting_for_category))
async def incorrect_category_input(message: types.Message, state: FSMContext):
    await message.answer("Пожалуйста, выберите категорию, используя кнопки выше.")