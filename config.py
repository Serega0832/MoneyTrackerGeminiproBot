# config.py
import os
import logging
from dotenv import load_dotenv

load_dotenv() # Загружает переменные из .env файла

BOT_TOKEN = os.getenv('BOT_TOKEN')

# --- Настройки SQLite ---
# Получаем имя файла из .env или используем значение по умолчанию
SQLITE_DB_FILE = os.getenv('SQLITE_DB_FILE', 'finance_bot.db')
logging.info(f"Using SQLite database file: {SQLITE_DB_FILE}")

# --- Категории (остаются без изменений) ---
EXPENSE_CATEGORIES = ["Еда", "Транспорт", "Жилье", "Связь", "Развлечения", "Одежда", "Здоровье", "Другое"]
INCOME_CATEGORIES = ["Зарплата", "Подработка", "Подарок", "Проценты", "Другое"]

# Убрана вся логика парсинга DATABASE_URL и связанные переменные
# Убрана функция is_db_configured() - она больше не нужна в таком виде