"""
Обработчики для управления категориями
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

from ..database import Database
from ..utils.keyboards import (
    get_category_management_keyboard,
    get_main_menu_keyboard,
    get_confirmation_keyboard,
)
from ..utils.formatters import format_category_list
from ..utils.parsers import validate_category_name

logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
WAITING_CATEGORY_NAME, WAITING_CATEGORY_ICON, WAITING_CATEGORY_EDIT = range(3)


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

    # Формируем клавиатуру с кнопками редактирования/удаления для каждой категории
    keyboard = []
    for cat in categories:
        keyboard.append([
            InlineKeyboardButton(f"✏️ {cat['name']}", callback_data=f"cat_edit:{cat['id']}"),
            InlineKeyboardButton(f"🗑️", callback_data=f"cat_delete:{cat['id']}"),
        ])
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="categories")])

    await query.edit_message_text(
        text + "\n\nВыберите категорию для редактирования:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ==================== СОЗДАНИЕ КАТЕГОРИИ ====================

async def add_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало создания новой категории"""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "➕ Создание новой категории\n\n"
        "Введите название категории (до 50 символов):",
        reply_markup=get_main_menu_keyboard()
    )

    return WAITING_CATEGORY_NAME


async def category_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка названия категории"""
    user_id = update.effective_user.id
    text = update.message.text.strip()

    db: Database = context.bot_data['db']

    # Валидация
    valid, error = validate_category_name(text)
    if not valid:
        await update.message.reply_text(f"❌ {error}\n\nВведите другое название:")
        return WAITING_CATEGORY_NAME

    # Проверка на дубликат
    existing = db.get_categories(user_id)
    if any(cat['name'].lower() == text.lower() for cat in existing):
        await update.message.reply_text(
            "❌ Категория с таким названием уже существует.\n\nВведите другое название:"
        )
        return WAITING_CATEGORY_NAME

    context.user_data['new_category_name'] = text

    # Предложим выбрать иконку
    icons_keyboard = [
        [InlineKeyboardButton("🍔", callback_data="icon:🍔"), InlineKeyboardButton("🚗", callback_data="icon:🚗"), InlineKeyboardButton("🏠", callback_data="icon:🏠")],
        [InlineKeyboardButton("💊", callback_data="icon:💊"), InlineKeyboardButton("👕", callback_data="icon:👕"), InlineKeyboardButton("🎮", callback_data="icon:🎮")],
        [InlineKeyboardButton("📚", callback_data="icon:📚"), InlineKeyboardButton("💰", callback_data="icon:💰"), InlineKeyboardButton("📦", callback_data="icon:📦")],
        [InlineKeyboardButton("✈️", callback_data="icon:✈️"), InlineKeyboardButton("🎁", callback_data="icon:🎁"), InlineKeyboardButton("🐾", callback_data="icon:🐾")],
        [InlineKeyboardButton("🔙 Использовать 📦", callback_data="icon:default")],
    ]
    await update.message.reply_text(
        "Выберите иконку для категории:",
        reply_markup=InlineKeyboardMarkup(icons_keyboard)
    )

    return WAITING_CATEGORY_ICON


async def category_icon_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора иконки"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']

    icon_data = query.data.split(':')[1]

    if icon_data == "default":
        icon = "📦"
    else:
        icon = icon_data

    name = context.user_data.get('new_category_name', 'Без названия')

    # Создание категории
    category_id = db.create_category(user_id, name, icon)

    if category_id:
        await query.edit_message_text(
            f"✅ Категория создана!\n\n"
            f"{icon} {name}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при создании категории",
            reply_markup=get_main_menu_keyboard()
        )

    context.user_data.clear()
    return ConversationHandler.END


# ==================== РЕДАКТИРОВАНИЕ КАТЕГОРИИ ====================

async def edit_category_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало редактирования категории"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']

    category_id = int(query.data.split(':')[1])
    category = db.get_category(category_id)

    if not category or category['user_id'] != user_id:
        await query.edit_message_text("❌ Категория не найдена")
        return ConversationHandler.END

    context.user_data['edit_category_id'] = category_id

    await query.edit_message_text(
        f"✏️ Редактирование категории\n\n"
        f"Текущее: {category['icon']} {category['name']}\n\n"
        f"Введите новое название (или отправьте «пропуск» чтобы оставить без изменений):",
        reply_markup=get_main_menu_keyboard()
    )

    return WAITING_CATEGORY_EDIT


async def category_edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нового названия категории"""
    user_id = update.effective_user.id
    text = update.message.text.strip()
    db: Database = context.bot_data['db']

    category_id = context.user_data.get('edit_category_id')
    category = db.get_category(category_id)

    if text.lower() == "пропуск":
        pass
    else:
        valid, error = validate_category_name(text)
        if not valid:
            await update.message.reply_text(f"❌ {error}\n\nВведите другое название:")
            return WAITING_CATEGORY_EDIT

        # Проверка на дубликат
        existing = db.get_categories(user_id)
        if any(cat['name'].lower() == text.lower() and cat['id'] != category_id for cat in existing):
            await update.message.reply_text(
                "❌ Категория с таким названием уже существует.\n\nВведите другое название:"
            )
            return WAITING_CATEGORY_EDIT

        context.user_data['new_category_name'] = text

    # Предложим выбрать иконку
    icons_keyboard = [
        [InlineKeyboardButton("🍔", callback_data="edit_icon:🍔"), InlineKeyboardButton("🚗", callback_data="edit_icon:🚗"), InlineKeyboardButton("🏠", callback_data="edit_icon:🏠")],
        [InlineKeyboardButton("💊", callback_data="edit_icon:💊"), InlineKeyboardButton("👕", callback_data="edit_icon:👕"), InlineKeyboardButton("🎮", callback_data="edit_icon:🎮")],
        [InlineKeyboardButton("📚", callback_data="edit_icon:📚"), InlineKeyboardButton("💰", callback_data="edit_icon:💰"), InlineKeyboardButton("📦", callback_data="edit_icon:📦")],
        [InlineKeyboardButton("✈️", callback_data="edit_icon:✈️"), InlineKeyboardButton("🎁", callback_data="edit_icon:🎁"), InlineKeyboardButton("🐾", callback_data="edit_icon:🐾")],
        [InlineKeyboardButton(f"🔙 Оставить {category['icon']}", callback_data="edit_icon:default")],
    ]
    await update.message.reply_text(
        "Выберите иконку для категории:",
        reply_markup=InlineKeyboardMarkup(icons_keyboard)
    )

    return WAITING_CATEGORY_ICON


async def category_edit_icon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора иконки при редактировании"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']

    icon_data = query.data.split(':')[1]
    category_id = context.user_data.get('edit_category_id')

    category = db.get_category(category_id)
    if icon_data == "default":
        icon = category['icon']
    else:
        icon = icon_data

    name = context.user_data.get('new_category_name', category['name'])

    # Обновление категории
    success = db.update_category(category_id, name=name, icon=icon)

    if success:
        await query.edit_message_text(
            f"✅ Категория обновлена!\n\n"
            f"{icon} {name}",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при обновлении категории",
            reply_markup=get_main_menu_keyboard()
        )

    context.user_data.clear()
    return ConversationHandler.END


# ==================== УДАЛЕНИЕ КАТЕГОРИИ ====================

async def delete_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Подтверждение удаления категории"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']

    category_id = int(query.data.split(':')[1])
    category = db.get_category(category_id)

    if not category or category['user_id'] != user_id:
        await query.edit_message_text("❌ Категория не найдена")
        return

    await query.edit_message_text(
        f"⚠️ Вы уверены, что хотите удалить категорию?\n\n"
        f"{category['icon']} {category['name']}\n\n"
        f"Расходы в этой категории НЕ будут удалены.",
        reply_markup=get_confirmation_keyboard(f"cat_delete:{category_id}")
    )


async def delete_category_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение удаления категории"""
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    db: Database = context.bot_data['db']

    category_id = int(query.data.split(':')[1])
    category = db.get_category(category_id)

    if not category or category['user_id'] != user_id:
        await query.edit_message_text("❌ Категория не найдена")
        return

    success = db.delete_category(category_id)

    if success:
        await query.edit_message_text(
            f"✅ Категория \"{category['name']}\" удалена",
            reply_markup=get_main_menu_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при удалении категории",
            reply_markup=get_main_menu_keyboard()
        )

    context.user_data.clear()


async def cancel_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена действия с категорией"""
    query = update.callback_query
    await query.answer("Отменено")

    await query.edit_message_text(
        "Действие отменено.\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


def register_category_handlers(application):
    """Регистрация обработчиков категорий"""

    # Conversation handler для создания категории
    add_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(add_category_start, pattern="^cat_add$"),
        ],
        states={
            WAITING_CATEGORY_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, category_name_received),
            ],
            WAITING_CATEGORY_ICON: [
                CallbackQueryHandler(category_icon_selected, pattern="^icon:"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_category, pattern="^cancel$"),
            CallbackQueryHandler(cancel_category, pattern="^main_menu$"),
        ],
    )

    # Conversation handler для редактирования категории
    edit_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_category_start, pattern="^cat_edit:\d+$"),
        ],
        states={
            WAITING_CATEGORY_EDIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, category_edit_name),
            ],
            WAITING_CATEGORY_ICON: [
                CallbackQueryHandler(category_edit_icon, pattern="^edit_icon:"),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_category, pattern="^cancel$"),
            CallbackQueryHandler(cancel_category, pattern="^main_menu$"),
        ],
    )

    application.add_handler(CommandHandler("categories", categories_command))
    application.add_handler(CallbackQueryHandler(categories_callback, pattern="^categories$"))
    application.add_handler(CallbackQueryHandler(category_list, pattern="^cat_list$"))
    application.add_handler(CallbackQueryHandler(delete_category_confirm, pattern="^cat_delete:\d+$"))
    application.add_handler(CallbackQueryHandler(delete_category_execute, pattern="^confirm:cat_delete:"))
    application.add_handler(add_conv)
    application.add_handler(edit_conv)
