"""
Генерация клавиатур для Telegram бота
"""
from typing import List, Dict, Any
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

from ..config import SUPPORTED_CURRENCIES, REPORT_PERIODS


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Главное меню бота"""
    keyboard = [
        [InlineKeyboardButton("💰 Добавить расход", callback_data="add_expense")],
        [InlineKeyboardButton("📊 Отчеты", callback_data="reports"),
         InlineKeyboardButton("🎯 Бюджет", callback_data="budget")],
        [InlineKeyboardButton("📋 Категории", callback_data="categories"),
         InlineKeyboardButton("💱 Валюта", callback_data="currency")],
        [InlineKeyboardButton("⚙️ Настройки", callback_data="settings"),
         InlineKeyboardButton("❓ Помощь", callback_data="help")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_categories_keyboard(categories: List[Dict[str, Any]], 
                           callback_prefix: str = "cat",
                           columns: int = 3) -> InlineKeyboardMarkup:
    """Клавиатура для выбора категории"""
    keyboard = []
    row = []
    
    for i, category in enumerate(categories):
        button = InlineKeyboardButton(
            f"{category['icon']} {category['name'][:15]}",
            callback_data=f"{callback_prefix}:{category['id']}"
        )
        row.append(button)
        
        if (i + 1) % columns == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Кнопка отмены
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


def get_currency_keyboard(current_currency: str = None) -> InlineKeyboardMarkup:
    """Клавиатура выбора валюты"""
    keyboard = []
    row = []
    
    for i, (code, info) in enumerate(SUPPORTED_CURRENCIES.items()):
        # Отметка текущей валюты
        prefix = "✅ " if code == current_currency else ""
        button = InlineKeyboardButton(
            f"{prefix}{code} {info['symbol']}",
            callback_data=f"currency:{code}"
        )
        row.append(button)
        
        if (i + 1) % 3 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel")])
    
    return InlineKeyboardMarkup(keyboard)


def get_report_period_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура выбора периода отчета"""
    keyboard = [
        [InlineKeyboardButton("📅 Неделя", callback_data="report:week"),
         InlineKeyboardButton("📅 Месяц", callback_data="report:month")],
        [InlineKeyboardButton("📅 Квартал", callback_data="report:quarter"),
         InlineKeyboardButton("📅 Год", callback_data="report:year")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_budget_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления бюджетом"""
    keyboard = [
        [InlineKeyboardButton("➕ Установить бюджет", callback_data="budget:set")],
        [InlineKeyboardButton("📋 Мои бюджеты", callback_data="budget:list")],
        [InlineKeyboardButton("📊 Статус бюджета", callback_data="budget:status")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_category_management_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура управления категориями"""
    keyboard = [
        [InlineKeyboardButton("📋 Мои категории", callback_data="cat_list")],
        [InlineKeyboardButton("➕ Добавить категорию", callback_data="cat_add")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_confirmation_keyboard(action: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения действия"""
    keyboard = [
        [InlineKeyboardButton("✅ Да", callback_data=f"confirm:{action}"),
         InlineKeyboardButton("❌ Нет", callback_data="cancel")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Кнопка возврата"""
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=callback_data)]]
    return InlineKeyboardMarkup(keyboard)


def get_expense_actions_keyboard(expense_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с расходом"""
    keyboard = [
        [InlineKeyboardButton("✏️ Изменить категорию", callback_data=f"move_expense:{expense_id}")],
        [InlineKeyboardButton("🗑️ Удалить расход", callback_data=f"expense_delete:{expense_id}")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_budget_list_keyboard(budgets: List[Dict[str, Any]]) -> InlineKeyboardMarkup:
    """Клавиатура списка бюджетов"""
    keyboard = []
    
    for budget in budgets:
        category_name = budget.get('category_name', 'Общий')
        icon = budget.get('category_icon', '💰')
        button = InlineKeyboardButton(
            f"{icon} {category_name}",
            callback_data=f"budget_view:{budget['id']}"
        )
        keyboard.append([button])
    
    keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="budget")])
    
    return InlineKeyboardMarkup(keyboard)


def get_settings_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура настроек"""
    keyboard = [
        [InlineKeyboardButton("💱 Изменить валюту", callback_data="settings:currency")],
        [InlineKeyboardButton("🕐 Часовой пояс", callback_data="settings:timezone")],
        [InlineKeyboardButton("📤 Экспорт данных", callback_data="export")],
        [InlineKeyboardButton("🔙 Назад", callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(keyboard)
