"""
Обработчики для управления бюджетом
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, ConversationHandler, MessageHandler, filters

from ..database import Database
from ..services import BudgetService, CurrencyService
from ..utils.keyboards import (
    get_budget_management_keyboard,
    get_categories_keyboard,
    get_budget_list_keyboard,
    get_main_menu_keyboard
)
from ..utils.parsers import parse_budget_amount, extract_callback_data
from ..utils.formatters import format_budget_status

logger = logging.getLogger(__name__)

# Состояния
WAITING_BUDGET_AMOUNT = range(1)


async def budget_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /budget"""
    await update.message.reply_text(
        "🎯 Управление бюджетом",
        reply_markup=get_budget_management_keyboard()
    )


async def budget_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback для бюджета"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🎯 Управление бюджетом",
        reply_markup=get_budget_management_keyboard()
    )


async def set_budget_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало установки бюджета"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    
    categories = db.get_categories(user_id)
    
    await query.edit_message_text(
        "🎯 Установка бюджета\n\n"
        "Выберите категорию (или общий бюджет):",
        reply_markup=get_categories_keyboard(categories, "budget_cat")
    )


async def budget_category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выбрана категория для бюджета"""
    query = update.callback_query
    await query.answer()

    action, category_id = extract_callback_data(query.data)
    context.user_data['budget_category_id'] = int(category_id)

    db: Database = context.bot_data['db']
    budget_service: BudgetService = context.bot_data['budget_service']
    currency_service: CurrencyService = context.bot_data['currency_service']

    category = db.get_category(int(category_id))
    user = db.get_user(update.effective_user.id)
    currency_symbol = currency_service.get_currency_symbol(user['default_currency'])

    # Проверка существующего бюджета
    existing_budget = budget_service.get_budget(update.effective_user.id, int(category_id))

    text = f"🎯 Установка бюджета для категории:\n"
    text += f"{category['icon']} {category['name']}\n\n"

    if existing_budget:
        text += f"Текущий лимит: {existing_budget['limit_amount']:,.2f} {currency_symbol}\n\n"

    text += f"Введите новую сумму лимита:"

    await query.edit_message_text(text)

    return WAITING_BUDGET_AMOUNT


async def budget_amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получена сумма бюджета"""
    user_id = update.effective_user.id
    text = update.message.text
    
    db: Database = context.bot_data['db']
    budget_service: BudgetService = context.bot_data['budget_service']
    currency_service: CurrencyService = context.bot_data['currency_service']
    
    amount = parse_budget_amount(text)
    
    if not amount or amount <= 0:
        await update.message.reply_text(
            "❌ Неверная сумма. Введите положительное число:"
        )
        return WAITING_BUDGET_AMOUNT
    
    category_id = context.user_data.get('budget_category_id')
    
    # Установка бюджета
    budget_id = budget_service.set_budget(user_id, amount, category_id)
    
    if budget_id:
        user = db.get_user(user_id)
        currency_symbol = currency_service.get_currency_symbol(user['default_currency'])
        
        category = db.get_category(category_id) if category_id else None
        category_name = f"{category['icon']} {category['name']}" if category else "Общий бюджет"
        
        await update.message.reply_text(
            f"✅ Бюджет установлен!\n\n"
            f"{category_name}\n"
            f"Лимит: {amount} {currency_symbol}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при установке бюджета",
            reply_markup=get_main_menu_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END


async def budget_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Список бюджетов"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    budget_service: BudgetService = context.bot_data['budget_service']
    currency_service: CurrencyService = context.bot_data['currency_service']

    budgets = budget_service.get_all_budgets(user_id)

    if not budgets:
        await query.edit_message_text(
            "У вас пока нет установленных бюджетов.\n\n"
            "Установите бюджет для контроля расходов!",
            reply_markup=get_budget_management_keyboard()
        )
        return

    user = db.get_user(user_id)
    currency_symbol = currency_service.get_currency_symbol(user['default_currency'])

    text = "📋 Ваши бюджеты:\n\n"
    for budget in budgets:
        category_name = budget.get('category_name', 'Общий бюджет')
        category_icon = budget.get('category_icon', '💰')
        limit_amount = budget['limit_amount']
        text += f"{category_icon} {category_name}: {limit_amount:,.2f} {currency_symbol}\n"

    text += "\nВыберите действие:"

    await query.edit_message_text(
        text,
        reply_markup=get_budget_management_keyboard()
    )


async def budget_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Статус всех бюджетов"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    budget_service: BudgetService = context.bot_data['budget_service']
    currency_service: CurrencyService = context.bot_data['currency_service']
    
    user = db.get_user(user_id)
    currency_symbol = currency_service.get_currency_symbol(user['default_currency'])
    
    summary = budget_service.get_budget_summary(user_id)
    
    if not summary['budgets']:
        await query.edit_message_text(
            "У вас пока нет установленных бюджетов.",
            reply_markup=get_budget_management_keyboard()
        )
        return
    
    text = "📊 Статус бюджетов\n\n"
    
    for budget_status in summary['budgets']:
        budget = budget_status['budget']
        text += format_budget_status(budget, budget_status['spent'], currency_symbol)
        text += "\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=get_budget_management_keyboard()
    )


async def cancel_budget(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена установки бюджета"""
    await update.message.reply_text(
        "Установка бюджета отменена.",
        reply_markup=get_main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


def register_budget_handlers(application):
    """Регистрация обработчиков бюджета"""
    
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(budget_category_selected, pattern="^budget_cat:"),
        ],
        states={
            WAITING_BUDGET_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, budget_amount_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_budget),
            CallbackQueryHandler(cancel_budget, pattern="^cancel$"),
        ],
    )
    
    application.add_handler(CommandHandler("budget", budget_command))
    application.add_handler(CallbackQueryHandler(budget_callback, pattern="^budget$"))
    application.add_handler(CallbackQueryHandler(set_budget_start, pattern="^budget:set$"))
    application.add_handler(CallbackQueryHandler(budget_list, pattern="^budget:list$"))
    application.add_handler(CallbackQueryHandler(budget_status, pattern="^budget:status$"))
    application.add_handler(conv_handler)
