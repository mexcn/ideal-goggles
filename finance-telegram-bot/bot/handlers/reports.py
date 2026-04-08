"""
Обработчики для отчетов
"""
import logging
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..services import ReportService
from ..utils.keyboards import get_report_period_keyboard, get_main_menu_keyboard
from ..utils.parsers import extract_callback_data

logger = logging.getLogger(__name__)


async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /report"""
    await update.message.reply_text(
        "📊 Выберите период для отчета:",
        reply_markup=get_report_period_keyboard()
    )


async def reports_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback для выбора отчета"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📊 Выберите период для отчета:",
        reply_markup=get_report_period_keyboard()
    )


async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерация отчета за выбранный период"""
    query = update.callback_query
    await query.answer("Генерируем отчет...")
    
    user_id = update.effective_user.id
    report_service: ReportService = context.bot_data['report_service']
    
    # Извлечение периода
    action, period = extract_callback_data(query.data)
    
    # Генерация текстового отчета
    text_report = report_service.generate_text_report(user_id, period)
    
    await query.edit_message_text(text_report)
    
    # Генерация графиков
    try:
        # Круговая диаграмма
        pie_chart = report_service.generate_pie_chart(user_id, period)
        if pie_chart:
            await query.message.reply_photo(
                photo=InputFile(pie_chart, filename="expenses_pie.png"),
                caption="📊 Распределение расходов по категориям"
            )
        
        # Столбчатая диаграмма
        bar_chart = report_service.generate_bar_chart(user_id, period)
        if bar_chart:
            await query.message.reply_photo(
                photo=InputFile(bar_chart, filename="expenses_bar.png"),
                caption="📈 Расходы по дням"
            )
    except Exception as e:
        logger.error(f"Ошибка при генерации графиков: {e}")
    
    # Главное меню
    await query.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /stats - быстрая статистика за месяц"""
    user_id = update.effective_user.id
    report_service: ReportService = context.bot_data['report_service']
    
    text_report = report_service.generate_text_report(user_id, 'month')
    
    await update.message.reply_text(
        text_report,
        reply_markup=get_main_menu_keyboard()
    )


def register_report_handlers(application):
    """Регистрация обработчиков отчетов"""
    application.add_handler(CommandHandler("report", report_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CallbackQueryHandler(reports_callback, pattern="^reports$"))
    application.add_handler(CallbackQueryHandler(generate_report, pattern="^report:"))
