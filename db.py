# db.py
import aiosqlite
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Union, List, Tuple, Dict # Используем typing для совместимости
import config

# Глобальная переменная для соединения с БД SQLite
db_conn: Optional[aiosqlite.Connection] = None

async def connect_db():
    global db_conn
    try:
        db_conn = await aiosqlite.connect(config.SQLITE_DB_FILE)
        db_conn.row_factory = aiosqlite.Row
        # Включаем поддержку внешних ключей (понадобится для каскадного удаления, если решим добавить)
        await db_conn.execute("PRAGMA foreign_keys = ON")
        logging.info(f"Successfully connected to SQLite database: {config.SQLITE_DB_FILE}")
        await init_db()
        return True
    except Exception as e:
        logging.error(f"Error connecting to SQLite database: {e}")
        db_conn = None
        return False

async def close_db():
    global db_conn
    if db_conn:
        try:
            await db_conn.close()
            logging.info("SQLite database connection closed.")
            db_conn = None
        except Exception as e:
            logging.error(f"Error closing SQLite database connection: {e}")

async def init_db():
    """Проверяет/создает таблицы transactions и user_categories."""
    global db_conn
    if not db_conn:
        logging.error("Cannot initialize DB: No active connection.")
        return

    create_transactions_table = """
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        transaction_type TEXT NOT NULL CHECK(transaction_type IN ('expense', 'income')),
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_transactions_index = """
    CREATE INDEX IF NOT EXISTS idx_user_month ON transactions (user_id, created_at);
    """
    # --- НОВОЕ: Таблица для пользовательских категорий ---
    create_user_categories_table = """
    CREATE TABLE IF NOT EXISTS user_categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        category_type TEXT NOT NULL CHECK(category_type IN ('expense', 'income')),
        category_name TEXT NOT NULL,
        -- Уникальность имени категории для пользователя и типа
        UNIQUE(user_id, category_type, category_name)
    );
    """
    # --- КОНЕЦ НОВОГО ---

    try:
        async with db_conn.cursor() as cursor:
            await cursor.execute(create_transactions_table)
            logging.info("Table 'transactions' checked/created.")
            await cursor.execute(create_transactions_index)
            logging.info("Index 'idx_user_month' checked/created.")
            # --- НОВОЕ: Создаем таблицу категорий ---
            await cursor.execute(create_user_categories_table)
            logging.info("Table 'user_categories' checked/created.")
            # --- КОНЕЦ НОВОГО ---

        await db_conn.commit()
        logging.info("SQLite schema initialization committed.")
    except Exception as e:
        logging.error(f"Error during SQLite schema initialization: {e}")

# --- Функции для транзакций (add_transaction, get_last_transaction..., delete_transaction..., get_period_summary..., get_recent...) ---
# --- Оставляем их без изменений (код из предыдущего ответа) ---
async def add_transaction(user_id: int, transaction_type: str, amount: float, category: str) -> bool:
    global db_conn
    if not db_conn: return False
    sql = "INSERT INTO transactions (user_id, transaction_type, amount, category) VALUES (?, ?, ?, ?)"
    try:
        await db_conn.execute(sql, (user_id, transaction_type, amount, category))
        await db_conn.commit()
        logging.info(f"SQLite Transaction added: User {user_id}, Type {transaction_type}, Amount {amount}, Cat {category}")
        return True
    except Exception as e:
        logging.error(f"Error adding transaction to SQLite for user {user_id}: {e}")
        return False

async def get_last_transaction_id_details(user_id: int) -> Optional[aiosqlite.Row]:
    global db_conn
    if not db_conn: return None
    sql = "SELECT * FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT 1"
    try:
        async with db_conn.execute(sql, (user_id,)) as cursor:
            return await cursor.fetchone()
    except Exception as e:
        logging.error(f"Error getting last transaction for user {user_id}: {e}")
        return None

async def delete_transaction_by_id(transaction_id: int, user_id: int) -> bool:
    global db_conn
    if not db_conn: return False
    sql = "DELETE FROM transactions WHERE id = ? AND user_id = ?"
    try:
        async with db_conn.execute(sql, (transaction_id, user_id)) as cursor:
             if cursor.rowcount == 0:
                  logging.warning(f"Transaction ID {transaction_id} not found or does not belong to user {user_id}.")
                  return False
        await db_conn.commit()
        logging.info(f"Transaction ID {transaction_id} deleted for user {user_id}.")
        return True
    except Exception as e:
        logging.error(f"Error deleting transaction ID {transaction_id} for user {user_id}: {e}")
        return False

async def get_period_summary_with_details(user_id: int, start_date: datetime, end_date: datetime) -> Tuple[float, float, Dict[str, float]]:
    global db_conn
    if not db_conn: return 0.0, 0.0, {}
    start_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
    end_str = end_date.strftime('%Y-%m-%d %H:%M:%S')
    sql_summary = "SELECT transaction_type, SUM(amount) as total_amount FROM transactions WHERE user_id = ? AND created_at >= ? AND created_at < ? GROUP BY transaction_type"
    sql_expense_details = "SELECT category, SUM(amount) as category_total FROM transactions WHERE user_id = ? AND transaction_type = 'expense' AND created_at >= ? AND created_at < ? GROUP BY category ORDER BY category_total DESC"
    total_income = 0.0
    total_expense = 0.0
    expense_details: Dict[str, float] = {}
    try:
        async with db_conn.execute(sql_summary, (user_id, start_str, end_str)) as cursor:
            results = await cursor.fetchall()
            for row in results:
                if row['transaction_type'] == 'income': total_income = float(row['total_amount'] or 0.0)
                elif row['transaction_type'] == 'expense': total_expense = float(row['total_amount'] or 0.0)
        async with db_conn.execute(sql_expense_details, (user_id, start_str, end_str)) as cursor:
            results = await cursor.fetchall()
            for row in results: expense_details[row['category']] = float(row['category_total'] or 0.0)
        logging.info(f"Period summary for user {user_id} ({start_str} to {end_str}): Income={total_income}, Expense={total_expense}, Details fetched={len(expense_details)>0}")
        return total_income, total_expense, expense_details
    except Exception as e:
        logging.error(f"Error getting period summary from SQLite for user {user_id}: {e}")
        return 0.0, 0.0, {}

async def get_recent_transactions(user_id: int, limit: int = 10) -> List[aiosqlite.Row]:
    global db_conn
    if not db_conn: return []
    sql = "SELECT created_at, transaction_type, amount, category FROM transactions WHERE user_id = ? ORDER BY id DESC LIMIT ?"
    try:
        async with db_conn.execute(sql, (user_id, limit)) as cursor:
            return await cursor.fetchall()
    except Exception as e:
        logging.error(f"Error getting recent transactions for user {user_id}: {e}")
        return []

# --- НОВЫЕ ФУНКЦИИ для управления категориями ---

async def get_user_categories(user_id: int, category_type: str) -> List[str]:
    """Получает список пользовательских категорий заданного типа."""
    global db_conn
    if not db_conn: return []
    sql = "SELECT category_name FROM user_categories WHERE user_id = ? AND category_type = ? ORDER BY category_name"
    try:
        async with db_conn.execute(sql, (user_id, category_type)) as cursor:
            rows = await cursor.fetchall()
            return [row['category_name'] for row in rows]
    except Exception as e:
        logging.error(f"Error getting user categories for user {user_id}, type {category_type}: {e}")
        return []

async def add_user_category(user_id: int, category_type: str, category_name: str) -> bool:
    """Добавляет новую категорию пользователя. Возвращает True при успехе, False при ошибке (в т.ч. дубликат)."""
    global db_conn
    if not db_conn: return False
    # Проверка на пустую строку
    if not category_name or category_name.isspace():
        logging.warning(f"Attempt to add empty category name for user {user_id}")
        return False
    # Нормализация имени (убрать лишние пробелы)
    normalized_name = category_name.strip()

    sql = "INSERT INTO user_categories (user_id, category_type, category_name) VALUES (?, ?, ?)"
    try:
        await db_conn.execute(sql, (user_id, category_type, normalized_name))
        await db_conn.commit()
        logging.info(f"User category added: User {user_id}, Type {category_type}, Name '{normalized_name}'")
        return True
    except aiosqlite.IntegrityError: # Ловим ошибку уникальности (дубликат)
        logging.warning(f"Duplicate category attempt: User {user_id}, Type {category_type}, Name '{normalized_name}'")
        return False # Возвращаем False при дубликате
    except Exception as e:
        logging.error(f"Error adding user category for user {user_id}: {e}")
        return False

async def delete_user_category(user_id: int, category_type: str, category_name: str) -> bool:
    """Удаляет пользовательскую категорию."""
    global db_conn
    if not db_conn: return False

    # Проверка, не пытается ли пользователь удалить стандартную категорию (если мы их тоже показываем)
    # Эту логику лучше делать на уровне интерфейса, но можно и здесь
    # if category_type == 'expense' and category_name in config.EXPENSE_CATEGORIES: return False
    # if category_type == 'income' and category_name in config.INCOME_CATEGORIES: return False

    sql = "DELETE FROM user_categories WHERE user_id = ? AND category_type = ? AND category_name = ?"
    try:
        async with db_conn.execute(sql, (user_id, category_type, category_name)) as cursor:
            if cursor.rowcount == 0:
                logging.warning(f"Category not found for deletion: User {user_id}, Type {category_type}, Name '{category_name}'")
                return False # Категория не найдена
        await db_conn.commit()
        logging.info(f"User category deleted: User {user_id}, Type {category_type}, Name '{category_name}'")
        return True
    except Exception as e:
        logging.error(f"Error deleting user category for user {user_id}: {e}")
        return False