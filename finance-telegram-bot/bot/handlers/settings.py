"""
Обработчики для настроек
"""
import logging
from datetime import date
from telegram import Update, InputFile
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..database import Database
from ..services import ReportService, CurrencyService
from ..utils.keyboards import get_settings_keyboard, get_currency_keyboard, get_main_menu_keyboard
from ..utils.parsers import extract_callback_data

logger = logging.getLogger(__name__)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /settings"""
    await update.message.reply_text(
        "⚙️ Настройки",
        reply_markup=get_settings_keyboard()
    )


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback для настроек"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "⚙️ Настройки",
        reply_markup=get_settings_keyboard()
    )


async def settings_currency(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изменение валюты"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    
    user = db.get_user(user_id)
    current_currency = user['default_currency'] if user else None
    
    await query.edit_message_text(
        "💱 Выберите валюту:",
        reply_markup=get_currency_keyboard(current_currency)
    )


async def currency_changed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка изменения валюты"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    currency_service: CurrencyService = context.bot_data['currency_service']
    
    action, currency_code = extract_callback_data(query.data)
    
    # Обновление валюты
    if db.update_user_currency(user_id, currency_code):
        currency_symbol = currency_service.get_currency_symbol(currency_code)
        
        await query.edit_message_text(
            f"✅ Валюта изменена на {currency_code} {currency_symbol}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при изменении валюты",
            reply_markup=get_settings_keyboard()
        )


async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспорт данных в CSV"""
    query = update.callback_query
    await query.answer("Экспортируем данные...")
    
    user_id = update.effective_user.id
    report_service: ReportService = context.bot_data['report_service']
    
    # Экспорт всех данных за последний год
    end_date = date.today()
    start_date = end_date.replace(year=end_date.year - 1)
    
    csv_file = report_service.export_to_csv(user_id, start_date, end_date)
    
    if csv_file:
        await query.message.reply_document(
            document=InputFile(csv_file, filename="expenses.csv"),
            caption="📤 Экспорт расходов за последний год"
        )
    else:
        await query.edit_message_text(
            "❌ Нет данных для экспорта",
            reply_markup=get_settings_keyboard()
        )


def register_settings_handlers(application):
    """Регистрация обработчиков настроек"""
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CallbackQueryHandler(settings_callback, pattern="^settings$"))
    application.add_handler(CallbackQueryHandler(settings_currency, pattern="^settings:currency$"))
    application.add_handler(CallbackQueryHandler(currency_changed, pattern="^currency:(?!$)"))
    application.add_handler(CallbackQueryHandler(export_command, pattern="^export$"))
