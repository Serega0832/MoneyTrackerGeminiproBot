# handlers/categories.py
import logging
from aiogram import Router, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.markdown import hbold
import keyboards as kb
import db
from states import CategoryManagementStates

categories_router = Router() # Роутер для управления категориями

# --- Обработчики Управления Категориями ---

# Вход в меню управления категориями (команда и кнопка)
@categories_router.message(F.text == "⚙️ Мои Категории", StateFilter(None))
@categories_router.message(Command("mycategories"), StateFilter(None))
async def process_manage_categories(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    expense_cats = await db.get_user_categories(user_id, 'expense')
    income_cats = await db.get_user_categories(user_id, 'income')

    expense_text = "\n".join([f"- {cat}" for cat in expense_cats]) if expense_cats else "Нет"
    income_text = "\n".join([f"- {cat}" for cat in income_cats]) if income_cats else "Нет"

    reply_text = f"⚙️ <b>Управление категориями</b>\n\n" \
                 f"<u>Ваши категории расходов:</u>\n{expense_text}\n\n" \
                 f"<u>Ваши категории доходов:</u>\n{income_text}\n\n" \
                 f"Выберите действие:"

    await message.answer(reply_text, reply_markup=kb.get_manage_categories_kb())
    await state.set_state(CategoryManagementStates.choosing_action)

# Обработка кнопок в меню управления категориями (и возврат в меню)
@categories_router.callback_query(StateFilter(CategoryManagementStates.choosing_action), F.data.startswith("cat_manage:"))
@categories_router.callback_query(F.data == "cat_manage_menu") # Обработчик для возврата в меню
async def process_manage_action_callback(callback_query: types.CallbackQuery, state: FSMContext):
    if callback_query.data == "cat_manage_menu":
        action = "menu"
    else:
        action = callback_query.data.split(":")[1]

    message = callback_query.message

    if action == "add":
        await state.set_state(CategoryManagementStates.choosing_type_to_add)
        await message.edit_text("Выберите тип категории для добавления:", reply_markup=kb.get_category_type_kb("cat_add_type:"))
    elif action == "delete":
        await state.set_state(CategoryManagementStates.choosing_type_to_delete)
        await message.edit_text("Выберите тип категории для удаления:", reply_markup=kb.get_category_type_kb("cat_del_type:"))
    elif action == "back":
        await state.clear()
        await message.edit_text("Вы вышли из управления категориями.", reply_markup=None)
        await message.answer("Возврат в главное меню.", reply_markup=kb.main_kb)
    elif action == "menu":
         # Вызываем функцию-обработчик главного меню категорий, чтобы обновить сообщение
         # Убираем кнопки из предыдущего сообщения
         try: await message.edit_reply_markup(reply_markup=None)
         except: pass # Игнорируем, если уже нет
         await process_manage_categories(message, state) # Вызываем хендлер

    await callback_query.answer()

# --- FSM для Добавления Категории ---

@categories_router.callback_query(StateFilter(CategoryManagementStates.choosing_type_to_add), F.data.startswith("cat_add_type:"))
async def process_add_category_type_callback(callback_query: types.CallbackQuery, state: FSMContext):
    category_type = callback_query.data.split(":")[1]
    await state.update_data(category_type_to_add=category_type)
    await state.set_state(CategoryManagementStates.waiting_for_name_to_add)
    type_text = "расхода" if category_type == 'expense' else "дохода"
    await callback_query.message.edit_text(f"Введите название новой категории {type_text}:", reply_markup=None)
    await callback_query.answer()

@categories_router.message(StateFilter(CategoryManagementStates.waiting_for_name_to_add))
async def process_add_category_name(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    category_type = user_data.get("category_type_to_add")
    category_name = message.text.strip()

    if not category_name:
        await message.answer("Название категории не может быть пустым. Попробуйте еще раз или /cancel.")
        return
    if len(category_name) > 50:
        await message.answer("Название слишком длинное (макс. 50). Попробуйте еще раз или /cancel.")
        return

    user_id = message.from_user.id
    success = await db.add_user_category(user_id, category_type, category_name)

    if success:
        await message.answer(f"✅ Категория '{category_name}' успешно добавлена!", reply_markup=kb.main_kb)
        await state.clear()
    else:
        await message.answer(f"❌ Не удалось добавить '{category_name}'. Возможно, она уже существует? Попробуйте другое название или /cancel.")


# --- FSM для Удаления Категории ---

@categories_router.callback_query(StateFilter(CategoryManagementStates.choosing_type_to_delete), F.data.startswith("cat_del_type:"))
async def process_delete_category_type_callback(callback_query: types.CallbackQuery, state: FSMContext):
    category_type = callback_query.data.split(":")[1]
    user_id = callback_query.from_user.id
    user_categories = await db.get_user_categories(user_id, category_type)

    await state.update_data(category_type_to_delete=category_type)
    await state.set_state(CategoryManagementStates.choosing_category_to_delete)

    type_text = "расходов" if category_type == 'expense' else "доходов"
    if not user_categories:
        await callback_query.message.edit_text(f"У вас нет пользовательских категорий {type_text} для удаления.", reply_markup=kb.get_categories_for_delete_kb([]))
    else:
        await callback_query.message.edit_text(f"Выберите категорию {type_text} для удаления:", reply_markup=kb.get_categories_for_delete_kb(user_categories))
    await callback_query.answer()

@categories_router.callback_query(StateFilter(CategoryManagementStates.choosing_category_to_delete), F.data.startswith("cat_delete_confirm:"))
async def process_delete_category_confirm_callback(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        category_name_to_delete = callback_query.data.split(":", 1)[1]
    except IndexError:
        logging.error(f"Invalid delete category callback data: {callback_query.data}")
        await callback_query.answer("Ошибка", show_alert=True); return

    user_data = await state.get_data(); category_type = user_data.get("category_type_to_delete"); user_id = callback_query.from_user.id
    success = await db.delete_user_category(user_id, category_type, category_name_to_delete)

    if success:
        await callback_query.message.edit_text(f"✅ Категория '{category_name_to_delete}' удалена.", reply_markup=None)
        await process_manage_categories(callback_query.message, state) # Показываем обновленное меню
        await callback_query.answer("Удалено!")
    else:
        await callback_query.message.answer(f"❌ Не удалось удалить '{category_name_to_delete}'.", reply_markup=kb.main_kb)
        await state.clear(); await callback_query.answer("Ошибка удаления", show_alert=True)

@categories_router.callback_query(StateFilter(CategoryManagementStates.choosing_category_to_delete), F.data == "no_cats_to_delete")
@categories_router.callback_query(StateFilter(CategoryManagementStates.choosing_category_to_delete), F.data == "cat_delete_choose_type")
async def process_delete_category_back_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(CategoryManagementStates.choosing_type_to_delete)
    await callback_query.message.edit_text("Выберите тип категории для удаления:", reply_markup=kb.get_category_type_kb("cat_del_type:"))
    await callback_query.answer()