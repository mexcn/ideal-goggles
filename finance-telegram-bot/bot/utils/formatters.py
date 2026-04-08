"""
Форматирование данных для отображения
"""
from datetime import datetime, date
from typing import Dict, Any, List

from ..config import SUPPORTED_CURRENCIES


def format_amount(amount: float, currency: str = "RUB", show_currency: bool = True) -> str:
    """
    Форматирование суммы с валютой
    1500.5 RUB -> "1 500.50 ₽"
    """
    # Форматирование числа с пробелами для тысяч
    formatted = f"{amount:,.2f}".replace(',', ' ')
    
    if show_currency:
        symbol = SUPPORTED_CURRENCIES.get(currency, {}).get('symbol', currency)
        return f"{formatted} {symbol}"
    
    return formatted


def format_date(dt: date, format_type: str = "short") -> str:
    """
    Форматирование даты
    short: 01.03.2026
    long: 1 марта 2026
    relative: Сегодня, Вчера, 2 дня назад
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt).date()
    
    if format_type == "short":
        return dt.strftime("%d.%m.%Y")
    
    elif format_type == "long":
        months = [
            'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
            'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря'
        ]
        return f"{dt.day} {months[dt.month - 1]} {dt.year}"
    
    elif format_type == "relative":
        today = date.today()
        delta = (today - dt).days
        
        if delta == 0:
            return "Сегодня"
        elif delta == 1:
            return "Вчера"
        elif delta == 2:
            return "Позавчера"
        elif delta < 7:
            return f"{delta} дня назад" if 2 <= delta <= 4 else f"{delta} дней назад"
        else:
            return dt.strftime("%d.%m.%Y")
    
    return dt.strftime("%d.%m.%Y")


def format_datetime(dt: datetime, format_type: str = "short") -> str:
    """
    Форматирование даты и времени
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    
    if format_type == "short":
        return dt.strftime("%d.%m.%Y %H:%M")
    elif format_type == "long":
        return dt.strftime("%d %B %Y, %H:%M:%S")
    
    return dt.strftime("%d.%m.%Y %H:%M")


def format_percentage(value: float, total: float) -> str:
    """
    Форматирование процента
    """
    if total == 0:
        return "0.0%"
    
    percent = (value / total) * 100
    return f"{percent:.1f}%"


def format_expense(expense: Dict[str, Any], currency_symbol: str = "₽") -> str:
    """
    Форматирование расхода для отображения
    """
    amount = format_amount(expense['amount_in_default'], show_currency=False)
    description = expense.get('description', 'Без описания')
    category_icon = expense.get('category_icon', '📦')
    category_name = expense.get('category_name', 'Прочее')
    expense_date = format_date(expense['expense_date'], 'relative')
    
    return f"{category_icon} {amount} {currency_symbol} - {description}\n📅 {expense_date}"


def format_category_list(categories: List[Dict[str, Any]]) -> str:
    """
    Форматирование списка категорий
    """
    if not categories:
        return "Нет категорий"
    
    lines = ["📋 Ваши категории:\n"]
    for i, cat in enumerate(categories, 1):
        icon = cat.get('icon', '📦')
        name = cat.get('name', 'Без названия')
        lines.append(f"{i}. {icon} {name}")
    
    return "\n".join(lines)


def format_budget_status(budget: Dict[str, Any], spent: float, currency_symbol: str = "₽") -> str:
    """
    Форматирование статуса бюджета
    """
    limit = budget['limit_amount']
    remaining = limit - spent
    percent = (spent / limit * 100) if limit > 0 else 0
    
    category_name = budget.get('category_name', 'Общий бюджет')
    category_icon = budget.get('category_icon', '💰')
    
    # Эмодзи в зависимости от процента использования
    if percent < 50:
        status_emoji = "✅"
    elif percent < 80:
        status_emoji = "⚠️"
    else:
        status_emoji = "🚨"
    
    lines = [
        f"{status_emoji} {category_icon} {category_name}",
        f"Лимит: {format_amount(limit, show_currency=False)} {currency_symbol}",
        f"Потрачено: {format_amount(spent, show_currency=False)} {currency_symbol} ({percent:.1f}%)",
        f"Осталось: {format_amount(remaining, show_currency=False)} {currency_symbol}",
    ]
    
    # Прогресс-бар
    bar_length = 10
    filled = int(bar_length * percent / 100)
    bar = "█" * filled + "░" * (bar_length - filled)
    lines.append(f"[{bar}]")
    
    return "\n".join(lines)


def format_report_header(period: str, start_date: date, end_date: date) -> str:
    """
    Форматирование заголовка отчета
    """
    period_names = {
        'week': 'Неделя',
        'month': 'Месяц',
        'quarter': 'Квартал',
        'year': 'Год',
    }
    
    period_name = period_names.get(period, 'Период')
    
    if period == 'month':
        months = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        month_name = months[start_date.month - 1]
        return f"📊 Отчет за {month_name} {start_date.year}"
    
    elif period == 'year':
        return f"📊 Отчет за {start_date.year} год"
    
    else:
        return f"📊 Отчет: {period_name}\n{format_date(start_date)} - {format_date(end_date)}"


def format_expenses_by_category(expenses_data: List[tuple], total: float, 
                                currency_symbol: str = "₽") -> str:
    """
    Форматирование расходов по категориям
    expenses_data: [(category_name, category_icon, amount), ...]
    """
    if not expenses_data:
        return "Нет расходов за этот период"
    
    lines = ["📊 По категориям:\n"]
    
    for name, icon, amount in expenses_data:
        percent = format_percentage(amount, total)
        amount_str = format_amount(amount, show_currency=False)
        lines.append(f"{icon} {name}: {amount_str} {currency_symbol} ({percent})")
    
    return "\n".join(lines)


def format_statistics(total: float, days: int, currency_symbol: str = "₽") -> str:
    """
    Форматирование статистики
    """
    avg_per_day = total / days if days > 0 else 0
    
    lines = [
        f"\n📈 Статистика:",
        f"Общие расходы: {format_amount(total, show_currency=False)} {currency_symbol}",
        f"Средний расход в день: {format_amount(avg_per_day, show_currency=False)} {currency_symbol}",
        f"Период: {days} дней",
    ]
    
    return "\n".join(lines)


def format_currency_info(currency_code: str, rate_to_usd: float = None) -> str:
    """
    Форматирование информации о валюте
    """
    info = SUPPORTED_CURRENCIES.get(currency_code, {})
    symbol = info.get('symbol', currency_code)
    name = info.get('name', currency_code)
    
    text = f"{symbol} {name} ({currency_code})"
    
    if rate_to_usd:
        text += f"\nКурс к USD: {rate_to_usd:.4f}"
    
    return text


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Обрезка текста до максимальной длины
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
