"""
Главный файл запуска Telegram бота для управления финансами
"""
import logging
import sys
from telegram import BotCommand
from telegram.ext import Application

from .config import TELEGRAM_BOT_TOKEN, CURRENCY_UPDATE_INTERVAL
from .database import Database
from .services import CurrencyService, ExpenseService, BudgetService, ReportService
from .handlers import (
    register_start_handlers,
    register_expense_handlers,
    register_report_handlers,
    register_budget_handlers,
    register_category_handlers,
    register_settings_handlers,
)

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Инициализация после запуска бота"""
    logger.info("Бот запущен и готов к работе!")
    
    # Установка команд бота для меню
    commands = [
        BotCommand("start", "Запустить бота"),
        BotCommand("help", "Помощь и инструкции"),
        BotCommand("add", "Добавить расход"),
        BotCommand("recent", "Последние расходы"),
        BotCommand("report", "Отчеты и графики"),
        BotCommand("budget", "Управление бюджетом"),
        BotCommand("categories", "Управление категориями"),
        BotCommand("stats", "Быстрая статистика"),
        BotCommand("settings", "Настройки"),
    ]
    
    await application.bot.set_my_commands(commands)
    logger.info("Команды бота установлены")
    
    # Обновление курсов валют
    currency_service: CurrencyService = application.bot_data['currency_service']
    
    if currency_service.should_update_rates(CURRENCY_UPDATE_INTERVAL):
        logger.info("Обновление курсов валют...")
        success = currency_service.update_rates()
        
        if not success:
            logger.warning("Не удалось обновить курсы, используются дефолтные значения")
            currency_service.set_default_rates()
    
    logger.info("Инициализация завершена")


async def post_shutdown(application: Application) -> None:
    """Очистка при завершении работы"""
    logger.info("Остановка бота...")


def main():
    """Главная функция запуска бота"""
    try:
        logger.info("=" * 50)
        logger.info("Finance Telegram Bot - Запуск")
        logger.info("=" * 50)
        
        # Инициализация базы данных
        logger.info("Инициализация базы данных...")
        db = Database()
        
        # Инициализация сервисов
        logger.info("Инициализация сервисов...")
        currency_service = CurrencyService(db)
        expense_service = ExpenseService(db, currency_service)
        budget_service = BudgetService(db, expense_service)
        report_service = ReportService(db, expense_service)
        
        # Создание приложения
        logger.info("Создание приложения Telegram...")
        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .post_init(post_init)
            .post_shutdown(post_shutdown)
            .build()
        )
        
        # Сохранение сервисов в bot_data для доступа из handlers
        application.bot_data['db'] = db
        application.bot_data['currency_service'] = currency_service
        application.bot_data['expense_service'] = expense_service
        application.bot_data['budget_service'] = budget_service
        application.bot_data['report_service'] = report_service
        
        # Регистрация обработчиков
        logger.info("Регистрация обработчиков команд...")
        register_start_handlers(application)
        register_expense_handlers(application)
        register_report_handlers(application)
        register_budget_handlers(application)
        register_category_handlers(application)
        register_settings_handlers(application)
        
        logger.info("Все обработчики зарегистрированы")
        
        # Запуск бота
        logger.info("Запуск polling...")
        logger.info("Бот готов принимать команды!")
        
        application.run_polling(
            allowed_updates=['message', 'callback_query'],
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        logger.info("Получен сигнал остановки (Ctrl+C)")
    except Exception as e:
        logger.error(f"Критическая ошибка при запуске бота: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
