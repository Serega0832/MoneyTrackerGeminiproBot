# main.py
import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramAPIError
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Импортируем наши модули
import config
import db
# --- ИЗМЕНЕНИЕ: Импортируем новый роутер ---
from handlers import common, transactions, categories, reports, deletion, custom_report

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Основная функция запуска
async def main():
    logging.info("Starting bot...")

    # Инициализация бота, хранилища и диспетчера
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # --- ИЗМЕНЕНИЕ: Регистрируем новый роутер ---
    dp.include_routers(
        common.common_router,
        transactions.transactions_router,
        categories.categories_router,
        reports.reports_router,
        deletion.deletion_router,
        custom_report.custom_report_router # <-- Добавляем роутер
    )
    logging.info("Routers included.")

    # --- ИЗМЕНЕНИЕ: Добавляем команду /customreport ---
    await bot.set_my_commands([
        types.BotCommand(command="/start", description="Начать работу / Сбросить"),
        types.BotCommand(command="/mycategories", description="Управление категориями"),
        types.BotCommand(command="/report", description="Отчет за текущий месяц"),
        types.BotCommand(command="/prevmonthreport", description="Отчет за прошлый месяц"),
        types.BotCommand(command="/customreport", description="Отчет за период"), # <-- Добавлена команда
        types.BotCommand(command="/recent", description="Показать последние записи"),
        types.BotCommand(command="/deletelast", description="Удалить последнюю запись"),
        types.BotCommand(command="/cancel", description="Отменить текущее действие"),
        types.BotCommand(command="/help", description="Помощь"),
    ])
    logging.info("Bot commands set.")

    # Подключаемся к БД
    if not await db.connect_db():
        logging.critical("Failed to connect to SQLite database. Application cannot start.")
        if bot.session: await bot.session.close()
        return
    logging.info("SQLite Database connected and table initialized.")

    # Удаляем вебхук перед запуском polling
    await bot.delete_webhook(drop_pending_updates=True)

    # Запускаем polling
    logging.info("Starting polling...")
    try:
        await dp.start_polling(bot)
    except TelegramAPIError as e:
         if "bot was blocked" in str(e).lower(): logging.warning(f"Bot was blocked by user: {e}")
         else: logging.error(f"Telegram API error during polling: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected non-API error during polling: {e}", exc_info=True)
    finally:
        logging.info("Shutting down bot...")
        await db.close_db()
        await dp.storage.close()
        if bot.session: await bot.session.close()
        logging.info("Bot shut down gracefully.")

# Точка входа
if __name__ == '__main__':
    try: asyncio.run(main())
    except (KeyboardInterrupt, SystemExit): logging.info("Bot stopped manually.")
    except Exception as e: logging.critical(f"Critical error during startup/runtime: {e}", exc_info=True)