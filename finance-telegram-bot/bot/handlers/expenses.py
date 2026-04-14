"""
Обработчики для работы с расходами
"""
import logging
import re
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from telegram.ext.filters import MessageFilter

from ..database import Database
from ..services import ExpenseService, BudgetService, CurrencyService
from ..utils.keyboards import get_categories_keyboard, get_main_menu_keyboard
from ..utils.parsers import parse_expense_text, extract_callback_data
from ..utils.formatters import format_expense, format_amount, format_date

logger = logging.getLogger(__name__)


class MoveExpenseFilter(filters.BaseFilter):
    """Кастомный фильтр для команды /move_ID"""
    name = "move_expense_filter"

    def filter(self, update) -> bool:
        text = getattr(update.effective_message, 'text', '') or ''
        return bool(re.match(r'^/move_\d+$', text))

move_expense_filter = MoveExpenseFilter()

# Состояния для ConversationHandler
WAITING_AMOUNT, WAITING_CATEGORY = range(2)


async def add_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /add"""
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    
    # Проверка регистрации
    if not db.get_user(user_id):
        await update.message.reply_text(
            "Сначала выполните команду /start для регистрации"
        )
        return
    
    # Получение категорий
    categories = db.get_categories(user_id)
    
    await update.message.reply_text(
        "💰 Добавление расхода\n\n"
        "Выберите категорию:",
        reply_markup=get_categories_keyboard(categories, "add_cat")
    )


async def add_expense_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback для начала добавления расхода"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    
    categories = db.get_categories(user_id)
    
    await query.edit_message_text(
        "💰 Добавление расхода\n\n"
        "Выберите категорию:",
        reply_markup=get_categories_keyboard(categories, "add_cat")
    )


async def category_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора категории"""
    query = update.callback_query
    await query.answer()
    
    # Извлечение category_id
    action, category_id = extract_callback_data(query.data)
    
    # Сохранение в context
    context.user_data['category_id'] = int(category_id)
    
    await query.edit_message_text(
        "💰 Введите сумму и описание расхода:\n\n"
        "Примеры:\n"
        "• 500\n"
        "• 500 обед в кафе\n"
        "• 100$ такси\n"
        "• 50€ книга"
    )
    
    return WAITING_AMOUNT


async def amount_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка введенной суммы и описания"""
    user_id = update.effective_user.id
    text = update.message.text

    db: Database = context.bot_data['db']
    expense_service: ExpenseService = context.bot_data['expense_service']
    budget_service: BudgetService = context.bot_data['budget_service']
    currency_service: CurrencyService = context.bot_data['currency_service']

    # Парсинг текста
    parsed = parse_expense_text(text)

    if not parsed or parsed['amount'] is None:
        await update.message.reply_text(
            "❌ Не удалось распознать сумму.\n\n"
            "Попробуйте еще раз в формате:\n"
            "• 500\n"
            "• 500 описание\n"
            "• 100$ описание"
        )
        return WAITING_AMOUNT

    category_id = context.user_data.get('category_id')

    # Добавление расхода
    expense_id = expense_service.add_expense(
        user_id=user_id,
        category_id=category_id,
        amount=parsed['amount'],
        currency=parsed['currency'],
        description=parsed['description']
    )

    if expense_id:
        # Получение информации о расходе
        expense = expense_service.get_expense(expense_id)
        user = db.get_user(user_id)
        currency_symbol = currency_service.get_currency_symbol(user['default_currency'])

        response = f"✅ Расход добавлен!\n\n"
        response += f"💰 {format_amount(expense['amount_in_default'], user['default_currency'], False)} {currency_symbol}\n"
        response += f"{expense['category_icon']} Категория: {expense['category_name']}\n"

        if expense['description']:
            response += f"📝 {expense['description']}\n"

        response += f"📅 {format_date(expense['expense_date'], 'long')}"

        # Проверка бюджета
        exceeded, warning = budget_service.check_budget_after_expense(
            user_id, category_id, expense['amount_in_default']
        )

        if warning:
            response += f"\n\n{warning}"

        await update.message.reply_text(
            response,
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при добавлении расхода. Попробуйте еще раз.",
            reply_markup=get_main_menu_keyboard()
        )

    # Устанавливаем флаг ПЕРЕД очисткой, чтобы quick_expense (группа 1) его увидел
    context.user_data['_conv_processed'] = True
    # Удаляем только category_id, не очищаем всё
    context.user_data.pop('category_id', None)

    return ConversationHandler.END


async def quick_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Быстрое добавление расхода из обычного сообщения
    Формат: "500 транспорт поездка на такси" -> автоматически определит категорию
    """
    # Пропускаем, если сообщение уже обработано ConversationHandler
    if context.user_data.get('_conv_processed'):
        context.user_data.pop('_conv_processed', None)
        return

    user_id = update.effective_user.id
    text = update.message.text

    db: Database = context.bot_data['db']

    # Проверка регистрации
    if not db.get_user(user_id):
        await update.message.reply_text(
            "Сначала выполните команду /start для регистрации"
        )
        return

    expense_service: ExpenseService = context.bot_data['expense_service']
    budget_service: BudgetService = context.bot_data['budget_service']
    currency_service: CurrencyService = context.bot_data['currency_service']

    # Парсинг текста
    parsed = parse_expense_text(text)

    if not parsed or parsed['amount'] is None:
        # Не похоже на расход, игнорируем
        return

    # Определение категории
    categories = db.get_categories(user_id)

    # Если категория определена парсером, ищем её в базе
    selected_category = None
    if parsed.get('category'):
        selected_category = next(
            (c for c in categories if c['name'] == parsed['category']),
            None
        )

    # Если категория не найдена, используем "Прочее"
    if not selected_category:
        selected_category = next((c for c in categories if c['name'] == 'Прочее'), None)

    if not selected_category:
        # Если категории "Прочее" нет, берем первую
        selected_category = categories[0] if categories else None

    if not selected_category:
        await update.message.reply_text("❌ Ошибка: категории не найдены")
        return

    # Добавление расхода
    expense_id = expense_service.add_expense(
        user_id=user_id,
        category_id=selected_category['id'],
        amount=parsed['amount'],
        currency=parsed['currency'],
        description=parsed['description']
    )

    if expense_id:
        expense = expense_service.get_expense(expense_id)
        user = db.get_user(user_id)
        currency_symbol = currency_service.get_currency_symbol(user['default_currency'])

        response = f"✅ Расход добавлен!\n\n"
        response += f"💰 {format_amount(expense['amount_in_default'], user['default_currency'], False)} {currency_symbol}\n"
        response += f"{expense['category_icon']} {expense['category_name']}\n"

        if expense['description']:
            response += f"📝 {expense['description']}"

        # Проверка бюджета
        exceeded, warning = budget_service.check_budget_after_expense(
            user_id, selected_category['id'], expense['amount_in_default']
        )

        if warning:
            response += f"\n\n{warning}"

        # Добавляем inline кнопку для редактирования и удаления
        from ..utils.keyboards import get_expense_actions_keyboard
        reply_markup = get_expense_actions_keyboard(expense_id)

        await update.message.reply_text(response, reply_markup=reply_markup)


async def move_expense_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало перемещения расхода в другую категорию"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    expense_id = int(query.data.split(':')[1])
    
    db: Database = context.bot_data['db']
    expense_service: ExpenseService = context.bot_data['expense_service']
    
    # Получение расхода
    expense = expense_service.get_expense(expense_id)
    
    if not expense or expense['user_id'] != user_id:
        await query.edit_message_text("❌ Расход не найден")
        return
    
    # Получение категорий
    categories = db.get_categories(user_id)
    
    await query.edit_message_text(
        f"Расход: {expense['amount_in_default']} ₽ - {expense['description']}\n"
        f"Текущая категория: {expense['category_icon']} {expense['category_name']}\n\n"
        f"Выберите новую категорию:",
        reply_markup=get_categories_keyboard(categories, f"move_to:{expense_id}")
    )


async def move_expense_to_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Перемещение расхода в выбранную категорию"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    callback_data = query.data

    logger.info(f"move_expense_to_category: callback_data={callback_data}, user_id={user_id}")

    # Извлечение expense_id и category_id из callback_data
    # Формат: "move_to:expense_id:category_id"
    parts = callback_data.split(':')
    if len(parts) < 3:
        logger.error(f"Неверный формат callback_data: {callback_data}")
        await query.edit_message_text("❌ Ошибка: неверный формат данных")
        return

    try:
        expense_id = int(parts[1])
        category_id = int(parts[2])
    except (ValueError, IndexError) as e:
        logger.error(f"Ошибка парсинга callback_data '{callback_data}': {e}")
        await query.edit_message_text("❌ Ошибка: неверный формат данных")
        return

    db: Database = context.bot_data['db']
    expense_service: ExpenseService = context.bot_data['expense_service']

    # Проверка принадлежности расхода
    expense = expense_service.get_expense(expense_id)
    if not expense or expense['user_id'] != user_id:
        await query.edit_message_text("❌ Расход не найден")
        return

    # Проверка принадлежности категории
    category = db.get_category(category_id)
    if not category or category['user_id'] != user_id:
        await query.edit_message_text("❌ Категория не найдена")
        return

    logger.info(f"Перемещение расхода {expense_id} в категорию {category_id}")

    # Обновление категории расхода
    success = expense_service.update_expense(expense_id, category_id=category_id)

    if success:
        expense = expense_service.get_expense(expense_id)
        await query.edit_message_text(
            f"✅ Расход перемещён!\n\n"
            f"Новая категория: {expense['category_icon']} {expense['category_name']}\n"
            f"Сумма: {expense['amount_in_default']} ₽\n"
            f"Описание: {expense['description'] or 'Без описания'}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при перемещении расхода",
            reply_markup=get_main_menu_keyboard()
        )


async def recent_expenses_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для просмотра последних расходов"""
    user_id = update.effective_user.id
    
    db: Database = context.bot_data['db']
    expense_service: ExpenseService = context.bot_data['expense_service']
    currency_service: CurrencyService = context.bot_data['currency_service']
    
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Сначала выполните /start")
        return
    
    # Получение последних 10 расходов
    expenses = expense_service.get_recent_expenses(user_id, limit=10)
    
    if not expenses:
        await update.message.reply_text("У вас пока нет расходов")
        return
    
    currency_symbol = currency_service.get_currency_symbol(user['default_currency'])
    
    response = "📋 Последние расходы:\n\n"
    
    for exp in expenses:
        response += f"{exp['category_icon']} {format_amount(exp['amount_in_default'], user['default_currency'], False)} {currency_symbol}"
        if exp['description']:
            response += f" - {exp['description']}"
        response += f"\n📅 {format_date(exp['expense_date'], 'relative')}\n"
        response += f"💡 Нажмите для изменения: /move_{exp['id']}\n\n"
    
    await update.message.reply_text(response)


async def move_expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для перемещения расхода /move_ID"""
    text = update.message.text.strip()

    # Проверяем формат /move_ID
    if not text.startswith('/move_'):
        return  # Не команда move, пропускаем

    try:
        expense_id = int(text.split('_')[1])
    except (IndexError, ValueError):
        await update.message.reply_text("❌ Неверный формат команды. Используйте /move_ID")
        return

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']
    expense_service: ExpenseService = context.bot_data['expense_service']

    # Получение расхода
    expense = expense_service.get_expense(expense_id)

    if not expense or expense['user_id'] != user_id:
        await update.message.reply_text("❌ Расход не найден")
        return

    # Получение категорий
    categories = db.get_categories(user_id)

    # Клавиатура с категориями + кнопка удаления
    from ..utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = get_categories_keyboard(categories, f"move_to:{expense_id}").inline_keyboard
    keyboard.append([
        InlineKeyboardButton("🗑️ Удалить расход", callback_data=f"expense_delete:{expense_id}")
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"Расход: {expense['amount_in_default']} ₽ - {expense['description']}\n"
        f"Текущая категория: {expense['category_icon']} {expense['category_name']}\n\n"
        f"Выберите новую категорию или удалите расход:",
        reply_markup=reply_markup
    )


async def cancel_expense(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена добавления расхода"""
    await update.message.reply_text(
        "Добавление расхода отменено.",
        reply_markup=get_main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


# ==================== УДАЛЕНИЕ РАСХОДА ====================

async def delete_expense_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления расхода"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    expense_service: ExpenseService = context.bot_data['expense_service']

    expense_id = int(query.data.split(':')[1])
    expense = expense_service.get_expense(expense_id)

    if not expense or expense['user_id'] != user_id:
        await query.edit_message_text("❌ Расход не найден")
        return

    from ..utils.keyboards import get_confirmation_keyboard
    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить этот расход?\n\n"
        f"💰 {expense['amount_in_default']} ₽\n"
        f"{expense['category_icon']} {expense['category_name']}\n"
        f"📝 {expense['description'] or 'Без описания'}\n"
        f"📅 {format_date(expense['expense_date'], 'long')}",
        reply_markup=get_confirmation_keyboard(f"expense_delete:{expense_id}")
    )


async def delete_expense_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение удаления расхода"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']

    expense_id = int(query.data.split(':')[1])
    expense_service: ExpenseService = context.bot_data['expense_service']

    expense = expense_service.get_expense(expense_id)

    if not expense or expense['user_id'] != user_id:
        await query.edit_message_text("❌ Расход не найден")
        return

    success = db.delete_expense(expense_id)

    if success:
        await query.edit_message_text(
            "✅ Расход удалён",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при удалении расхода",
            reply_markup=get_main_menu_keyboard()
        )

    context.user_data.clear()


def register_expense_handlers(application):
    """Регистрация обработчиков расходов"""
    
    # Conversation handler для добавления расхода
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(category_selected, pattern="^add_cat:"),
        ],
        states={
            WAITING_AMOUNT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, amount_received)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_expense),
            CallbackQueryHandler(cancel_expense, pattern="^cancel$"),
        ],
    )
    
    application.add_handler(CommandHandler("add", add_expense_command))
    application.add_handler(CommandHandler("recent", recent_expenses_command))
    application.add_handler(CommandHandler("expenses", recent_expenses_command))
    
    # Обработчик команд перемещения /move_ID
    application.add_handler(MessageHandler(
        move_expense_filter,
        move_expense_command
    ))
    
    application.add_handler(CallbackQueryHandler(add_expense_callback, pattern="^add_expense$"))
    application.add_handler(CallbackQueryHandler(move_expense_start, pattern="^move_expense:"))
    application.add_handler(CallbackQueryHandler(move_expense_to_category, pattern="^move_to:"))
    application.add_handler(CallbackQueryHandler(delete_expense_confirm, pattern="^expense_delete:\d+$"))
    application.add_handler(CallbackQueryHandler(delete_expense_execute, pattern="^confirm:expense_delete:"))
    application.add_handler(conv_handler)
    
    # Обработчик быстрого добавления расходов (обычные текстовые сообщения)
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            quick_expense
        ),
        group=1  # Низкий приоритет, чтобы не перехватывать другие handlers
    )
