# handlers/deletion.py
import logging
from aiogram import Router, types, F, Bot # Добавили Bot для edit_message_reply_markup
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
import keyboards as kb
import db

deletion_router = Router() # Роутер для удаления

@deletion_router.message(F.text == "❌ Удалить последнее", StateFilter(None))
@deletion_router.message(Command("deletelast"), StateFilter(None))
async def process_delete_last(message: types.Message, state: FSMContext):
    await state.clear(); user_id = message.from_user.id; last_trans = await db.get_last_transaction_id_details(user_id)
    if not last_trans: await message.answer("Нет записей для удаления.", reply_markup=kb.main_kb); return
    trans_id = last_trans['id']; trans_type = "Доход" if last_trans['transaction_type'] == 'income' else "Расход"
    amount = last_trans['amount']; category = last_trans['category']
    confirm_text = f"Удалить последнюю запись?\n\nТип: {trans_type}\nСумма: {amount:.2f}\nКатегория: {category}"
    await message.answer(confirm_text, reply_markup=kb.get_delete_confirmation_kb(trans_id))

# Обработчик колбэков удаления
@deletion_router.callback_query(F.data.startswith("delete_"))
async def process_delete_callback(callback_query: types.CallbackQuery, state: FSMContext, bot: Bot): # Добавили bot
    action_data = callback_query.data.split(":")
    action = action_data[0]
    try:
        # Используем bot из аргументов функции
        await bot.edit_message_reply_markup(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id, reply_markup=None)
    except Exception: pass
    if action == "delete_confirm":
        try: transaction_id = int(action_data[1])
        except (IndexError, ValueError): logging.error(f"Invalid delete confirm cb data: {callback_query.data}"); await callback_query.message.answer("Ошибка удаления.", reply_markup=kb.main_kb); await callback_query.answer("Ошибка", show_alert=True); return
        success = await db.delete_transaction_by_id(transaction_id, callback_query.from_user.id)
        if success: await callback_query.message.answer("✅ Запись удалена.", reply_markup=kb.main_kb); await callback_query.answer("Удалено!")
        else: await callback_query.message.answer("❌ Не удалось удалить.", reply_markup=kb.main_kb); await callback_query.answer("Не удалено", show_alert=True)
    elif action == "delete_cancel": await callback_query.message.answer("Удаление отменено.", reply_markup=kb.main_kb); await callback_query.answer("Отменено")
    else: await callback_query.answer()