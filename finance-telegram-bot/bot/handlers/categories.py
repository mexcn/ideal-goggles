"""
Обработчики для управления категориями
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from ..database import Database
from ..utils.keyboards import get_category_management_keyboard, get_main_menu_keyboard
from ..utils.formatters import format_category_list

logger = logging.getLogger(__name__)


async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /categories"""
    await update.message.reply_text(
        "📋 Управление категориями",
        reply_markup=get_category_management_keyboard()
    )


async def categories_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback для категорий"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📋 Управление категориями",
        reply_markup=get_category_management_keyboard()
    )


async def category_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список категорий"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    
    categories = db.get_categories(user_id)
    
    text = format_category_list(categories)
    
    await query.edit_message_text(
        text,
        reply_markup=get_category_management_keyboard()
    )


def register_category_handlers(application):
    """Регистрация обработчиков категорий"""
    application.add_handler(CommandHandler("categories", categories_command))
    application.add_handler(CallbackQueryHandler(categories_callback, pattern="^categories$"))
    application.add_handler(CallbackQueryHandler(category_list, pattern="^cat_list$"))
