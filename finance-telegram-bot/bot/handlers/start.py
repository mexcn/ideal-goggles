"""
Обработчики команд /start и /help
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..config import MESSAGES
from ..database import Database
from ..services import CurrencyService
from ..utils.keyboards import get_main_menu_keyboard, get_currency_keyboard

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    user = update.effective_user
    db: Database = context.bot_data['db']
    
    # Проверка, существует ли пользователь
    existing_user = db.get_user(user.id)
    
    if existing_user:
        # Пользователь уже зарегистрирован
        await update.message.reply_text(
            f"С возвращением, {user.first_name}! 👋\n\n"
            "Выберите действие:",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        # Новый пользователь - выбор валюты
        await update.message.reply_text(
            MESSAGES['welcome'],
            reply_markup=get_currency_keyboard()
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /help"""
    await update.message.reply_text(
        MESSAGES['help'],
        reply_markup=get_main_menu_keyboard()
    )


async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка callback для справки"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        MESSAGES['help'],
        reply_markup=get_main_menu_keyboard()
    )


async def currency_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора валюты при регистрации"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    db: Database = context.bot_data['db']
    currency_service: CurrencyService = context.bot_data['currency_service']
    
    # Извлечение кода валюты из callback_data
    currency_code = query.data.split(':')[1]
    
    # Создание пользователя
    db.create_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        default_currency=currency_code
    )
    
    currency_symbol = currency_service.get_currency_symbol(currency_code)
    
    await query.edit_message_text(
        MESSAGES['currency_set'].format(
            currency=currency_code,
            symbol=currency_symbol
        )
    )
    
    # Отправка главного меню
    await query.message.reply_text(
        "Начните добавлять расходы! 💰\n\n"
        "Быстрый способ:\n"
        "Просто отправьте сумму и описание, например:\n"
        "• 500\n"
        "• 500 обед\n"
        "• 100$ кофе\n\n"
        "Или выберите действие из меню:",
        reply_markup=get_main_menu_keyboard()
    )


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возврат в главное меню"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена действия"""
    query = update.callback_query
    await query.answer("Отменено")
    
    await query.edit_message_text(
        "Действие отменено.\n\nВыберите другое действие:",
        reply_markup=get_main_menu_keyboard()
    )


def register_start_handlers(application):
    """Регистрация обработчиков стартовых команд"""
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Callback handlers
    application.add_handler(CallbackQueryHandler(currency_selection, pattern="^currency:"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(cancel_callback, pattern="^cancel$"))
