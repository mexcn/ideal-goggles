"""
Главный файл запуска Telegram бота для управления финансами
"""
import logging
import os
import sys
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import BotCommand
from telegram.ext import Application
from telegram.request import HTTPXRequest

from .config import TELEGRAM_BOT_TOKEN, CURRENCY_UPDATE_INTERVAL, DEFAULT_TIMEZONE
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
    scheduler = application.bot_data.get('scheduler')
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Планировщик остановлен")


async def daily_reminder(application: Application) -> None:
    """Ежедневное напоминание о добавлении расходов"""
    db: Database = application.bot_data.get('db')
    if not db:
        return

    # Получаем всех активных пользователей
    try:
        users = db.get_all_users()
    except AttributeError:
        logger.warning("Метод get_all_users() не найден в Database")
        return

    if not users:
        return

    message = (
        "🔔 Напоминание\n\n"
        "Не забудь добавить траты за день!\n\n"
        "Просто отправь сумму и описание, например:\n"
        "• 500 обед\n"
        "• 1000 продукты"
    )

    sent_count = 0
    for user in users:
        try:
            await application.bot.send_message(
                chat_id=user['user_id'],
                text=message
            )
            sent_count += 1
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {user['user_id']}: {e}")

    logger.info(f"Ежедневное напоминание: отправлено {sent_count}/{len(users)} пользователям")


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

        # Настройка прокси и таймаутов
        proxy_url = os.getenv("PROXY_URL")
        read_timeout = int(os.getenv("TELEGRAM_READ_TIMEOUT", "30"))
        connect_timeout = int(os.getenv("TELEGRAM_CONNECT_TIMEOUT", "30"))

        request = HTTPXRequest(
            connection_pool_size=8,
            read_timeout=read_timeout,
            connect_timeout=connect_timeout,
            proxy=proxy_url if proxy_url else None,
        )

        application = (
            Application.builder()
            .token(TELEGRAM_BOT_TOKEN)
            .request(request)
            .post_init(post_init)
            .post_shutdown(post_shutdown)
            .build()
        )

        # Обработчик ошибок
        async def error_handler(update, context):
            """Глобальный обработчик ошибок"""
            logger.error("Необработанная ошибка:", exc_info=context.error)

        application.add_error_handler(error_handler)
        
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

        # Настройка планировщика для ежедневных напоминаний
        reminder_hour = int(os.getenv("REMINDER_HOUR", "21"))
        reminder_minute = int(os.getenv("REMINDER_MINUTE", "0"))

        scheduler = AsyncIOScheduler(timezone=DEFAULT_TIMEZONE)
        scheduler.add_job(
            daily_reminder,
            'cron',
            hour=reminder_hour,
            minute=reminder_minute,
            args=[application],
            id='daily_reminder',
            name='Ежедневное напоминание о тратах',
            replace_existing=True,
        )
        scheduler.start()
        logger.info(f"Планировщик запущен: напоминание в {reminder_hour:02d}:{reminder_minute:02d}")

        # Сохраняем scheduler для остановки при shutdown
        application.bot_data['scheduler'] = scheduler

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
