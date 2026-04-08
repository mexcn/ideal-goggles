"""
Парсеры для обработки пользовательского ввода
"""
import re
from typing import Optional, Tuple, Dict
from datetime import datetime

from ..config import SUPPORTED_CURRENCIES


def parse_expense_text(text: str) -> Optional[Dict[str, any]]:
    """
    Парсинг текста расхода от пользователя
    
    Форматы:
    - "500" -> {'amount': 500.0, 'currency': None, 'category': None, 'description': ''}
    - "500 обед" -> {'amount': 500.0, 'currency': None, 'category': 'Еда и напитки', 'description': 'обед'}
    - "500 транспорт поездка на такси" -> {'amount': 500.0, 'category': 'Транспорт', 'description': 'поездка на такси'}
    - "100$ кофе" -> {'amount': 100.0, 'currency': 'USD', 'category': 'Еда и напитки', 'description': 'кофе'}
    """
    text = text.strip()
    
    if not text:
        return None
    
    result = {
        'amount': None,
        'currency': None,
        'category': None,
        'description': ''
    }
    
    # Регулярные выражения для поиска суммы и валюты
    # Поддержка форматов: 500, 500.50, 500,50, 500$, 500₽, $500
    
    # Паттерн для суммы с символом валюты после числа
    pattern1 = r'^(\d+[.,]?\d*)\s*([₽$€£¥₸])?(.*)$'
    # Паттерн для символа валюты перед числом
    pattern2 = r'^([₽$€£¥₸])\s*(\d+[.,]?\d*)(.*)$'
    # Паттерн для кода валюты (RUB, USD и т.д.)
    pattern3 = r'^(\d+[.,]?\d*)\s+([A-Z]{3})(.*)$'
    
    match = re.match(pattern3, text, re.IGNORECASE)
    if match:
        amount_str = match.group(1).replace(',', '.')
        currency_code = match.group(2).upper()
        description = match.group(3).strip()
        
        try:
            result['amount'] = float(amount_str)
            if currency_code in SUPPORTED_CURRENCIES:
                result['currency'] = currency_code
            result['category'], result['description'] = _extract_category_from_text(description)
            return result
        except ValueError:
            pass
    
    match = re.match(pattern1, text)
    if match:
        amount_str = match.group(1).replace(',', '.')
        currency_symbol = match.group(2)
        description = match.group(3).strip()
        
        try:
            result['amount'] = float(amount_str)
            result['currency'] = _symbol_to_currency(currency_symbol)
            result['category'], result['description'] = _extract_category_from_text(description)
            return result
        except ValueError:
            pass
    
    match = re.match(pattern2, text)
    if match:
        currency_symbol = match.group(1)
        amount_str = match.group(2).replace(',', '.')
        description = match.group(3).strip()
        
        try:
            result['amount'] = float(amount_str)
            result['currency'] = _symbol_to_currency(currency_symbol)
            result['category'], result['description'] = _extract_category_from_text(description)
            return result
        except ValueError:
            pass
    
    return None


def _extract_category_from_text(text: str) -> Tuple[Optional[str], str]:
    """
    Извлечение категории из текста по ключевым словам
    Возвращает (category_name, remaining_description)
    """
    if not text:
        return None, ''
    
    text_lower = text.lower()
    
    # Словарь категорий и их ключевых слов
    category_keywords = {
        'Еда и напитки': [
            'еда', 'обед', 'ужин', 'завтрак', 'кафе', 'ресторан', 'кофе',
            'чай', 'перекус', 'пицца', 'бургер', 'суши', 'напиток', 'вода',
            'продукты', 'магазин', 'супермаркет', 'покупка', 'молоко', 'хлеб'
        ],
        'Транспорт': [
            'транспорт', 'такси', 'метро', 'автобус', 'трамвай', 'маршрутка',
            'поездка', 'проезд', 'бензин', 'заправка', 'парковка', 'штраф',
            'uber', 'яндекс', 'каршеринг', 'электричка', 'поезд'
        ],
        'Жилье': [
            'жилье', 'аренда', 'квартплата', 'коммуналка', 'ипотека', 'дом',
            'квартира', 'жкх', 'электричество', 'вода', 'газ', 'интернет',
            'связь', 'ремонт', 'мебель'
        ],
        'Здоровье': [
            'здоровье', 'аптека', 'лекарства', 'врач', 'больница', 'клиника',
            'таблетки', 'анализы', 'медицина', 'стоматолог', 'лечение',
            'витамины', 'массаж', 'спорт', 'фитнес', 'зал'
        ],
        'Одежда': [
            'одежда', 'обувь', 'куртка', 'штаны', 'рубашка', 'платье', 'юбка',
            'кроссовки', 'ботинки', 'магазин', 'shopping', 'шоппинг', 'покупка',
            'футболка', 'джинсы', 'пальто'
        ],
        'Развлечения': [
            'развлечения', 'кино', 'театр', 'концерт', 'выставка', 'музей',
            'клуб', 'бар', 'паб', 'игры', 'ps', 'xbox', 'steam', 'подписка',
            'netflix', 'spotify', 'отдых', 'досуг', 'хобби'
        ],
        'Образование': [
            'образование', 'курсы', 'обучение', 'книга', 'учеба', 'университет',
            'школа', 'репетитор', 'семинар', 'тренинг', 'книги', 'подписка',
            'udemy', 'coursera', 'литература'
        ],
    }
    
    # Поиск категории по ключевым словам
    words = text_lower.split()
    
    for category, keywords in category_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                # Удаляем ключевое слово из описания
                remaining = text
                # Пытаемся удалить только первое вхождение ключевого слова
                for word in words:
                    if keyword in word.lower():
                        remaining = remaining.replace(word, '', 1).strip()
                        break
                
                # Очистка от лишних пробелов
                remaining = ' '.join(remaining.split())
                
                return category, remaining
    
    # Если категория не найдена, возвращаем весь текст как описание
    return None, text


def _symbol_to_currency(symbol: Optional[str]) -> Optional[str]:
    """Конвертация символа валюты в код"""
    if not symbol:
        return None
    
    symbol_map = {
        '₽': 'RUB',
        '$': 'USD',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'CNY',
        '₸': 'KZT',
    }
    
    return symbol_map.get(symbol)


def parse_amount(text: str) -> Optional[float]:
    """
    Парсинг суммы из текста
    Поддержка форматов: 500, 500.50, 500,50
    """
    text = text.strip().replace(',', '.')
    
    # Удаление всех нецифровых символов кроме точки
    text = re.sub(r'[^\d.]', '', text)
    
    try:
        amount = float(text)
        return amount if amount > 0 else None
    except (ValueError, TypeError):
        return None


def validate_category_name(name: str) -> Tuple[bool, str]:
    """
    Валидация имени категории
    Возвращает (valid, error_message)
    """
    name = name.strip()
    
    if not name:
        return False, "Название категории не может быть пустым"
    
    if len(name) > 50:
        return False, "Название категории слишком длинное (максимум 50 символов)"
    
    # Проверка на допустимые символы
    if not re.match(r'^[\w\s\-]+$', name, re.UNICODE):
        return False, "Название содержит недопустимые символы"
    
    return True, ""


def parse_budget_amount(text: str) -> Optional[float]:
    """Парсинг суммы бюджета"""
    return parse_amount(text)


def extract_callback_data(callback_data: str) -> Tuple[str, Optional[str]]:
    """
    Извлечение действия и параметра из callback_data
    Формат: "action:param"
    """
    parts = callback_data.split(':', 1)
    action = parts[0]
    param = parts[1] if len(parts) > 1 else None
    return action, param


def format_expense_input(text: str) -> str:
    """
    Форматирование ввода расхода для отображения
    """
    parsed = parse_expense_text(text)
    
    if not parsed or parsed['amount'] is None:
        return text
    
    amount = parsed['amount']
    currency = parsed['currency'] or '?'
    description = parsed['description'] or 'без описания'
    
    return f"{amount} {currency} - {description}"
