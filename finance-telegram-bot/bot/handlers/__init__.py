"""
Обработчики команд и сообщений бота
"""

from .start import register_start_handlers
from .expenses import register_expense_handlers
from .reports import register_report_handlers
from .budget import register_budget_handlers
from .categories import register_category_handlers
from .settings import register_settings_handlers

__all__ = [
    "register_start_handlers",
    "register_expense_handlers",
    "register_report_handlers",
    "register_budget_handlers",
    "register_category_handlers",
    "register_settings_handlers",
]
