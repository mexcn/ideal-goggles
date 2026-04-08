"""
Конфигурация бота и константы
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Базовые пути
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
LOGS_DIR = BASE_DIR / "logs"
BACKUP_DIR = DATA_DIR / "backups"

# Создание директорий
DATA_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
BACKUP_DIR.mkdir(exist_ok=True)

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не установлен в .env файле")

# Exchange Rate API
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
EXCHANGE_API_URL = os.getenv("EXCHANGE_API_URL", "https://v6.exchangerate-api.com/v6")

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "finance_bot.db"))

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE", str(LOGS_DIR / "bot.log"))

# Currency
CURRENCY_UPDATE_INTERVAL = int(os.getenv("CURRENCY_UPDATE_INTERVAL", "6"))
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "RUB")
DEFAULT_TIMEZONE = os.getenv("DEFAULT_TIMEZONE", "Europe/Moscow")

# Backup
BACKUP_ENABLED = os.getenv("BACKUP_ENABLED", "true").lower() == "true"
BACKUP_INTERVAL_DAYS = int(os.getenv("BACKUP_INTERVAL_DAYS", "7"))
BACKUP_PATH = os.getenv("BACKUP_PATH", str(BACKUP_DIR))

# Поддерживаемые валюты
SUPPORTED_CURRENCIES = {
    "RUB": {"symbol": "₽", "name": "Российский рубль"},
    "USD": {"symbol": "$", "name": "Доллар США"},
    "EUR": {"symbol": "€", "name": "Евро"},
    "GBP": {"symbol": "£", "name": "Фунт стерлингов"},
    "CNY": {"symbol": "¥", "name": "Китайский юань"},
    "KZT": {"symbol": "₸", "name": "Казахстанский тенге"},
}

# Предустановленные категории расходов
DEFAULT_CATEGORIES = [
    {"name": "Еда и напитки", "icon": "🍔", "color": "#FF6B6B"},
    {"name": "Транспорт", "icon": "🚗", "color": "#4ECDC4"},
    {"name": "Жилье", "icon": "🏠", "color": "#45B7D1"},
    {"name": "Здоровье", "icon": "💊", "color": "#96CEB4"},
    {"name": "Одежда", "icon": "👕", "color": "#FFEAA7"},
    {"name": "Развлечения", "icon": "🎮", "color": "#DFE6E9"},
    {"name": "Образование", "icon": "📚", "color": "#A29BFE"},
    {"name": "Прочее", "icon": "💰", "color": "#B2BEC3"},
]

# Периоды отчетов
REPORT_PERIODS = {
    "week": {"name": "Неделя", "days": 7},
    "month": {"name": "Месяц", "days": 30},
    "quarter": {"name": "Квартал", "days": 90},
    "year": {"name": "Год", "days": 365},
}

# Сообщения
MESSAGES = {
    "welcome": """👋 Добро пожаловать в Finance Bot!

Я помогу вам управлять личными финансами:
💰 Учет расходов
📊 Отчеты и статистика
🎯 Планирование бюджета
💱 Поддержка разных валют

Для начала выберите вашу основную валюту.""",
    
    "help": """📖 Справка по командам

💰 Основные команды:
/add - Добавить расход
/report - Получить отчет
/budget - Управление бюджетом
/categories - Управление категориями
/currency - Настройка валюты

⚙️ Дополнительные:
/stats - Статистика
/export - Экспорт данных
/settings - Настройки

❓ Быстрое добавление:
Просто отправьте сумму и описание:
• "500" - расход 500₽
• "500 еда" - 500₽ с описанием
• "100$ такси" - 100$ с описанием

💡 Советы:
• Используйте категории для точного учета
• Проверяйте отчеты регулярно
• Установите бюджеты для контроля расходов""",
    
    "currency_set": "✅ Валюта установлена: {currency} {symbol}\n\nДля вас созданы базовые категории расходов.",
    
    "expense_added": """✅ Расход добавлен!

💰 {amount} {symbol} - {description}
{icon} Категория: {category}
📅 Дата: {date}""",
    
    "budget_warning": "⚠️ Внимание! Использовано {percent}% бюджета категории \"{category}\"",
    "budget_exceeded": "🚨 Бюджет категории \"{category}\" превышен!",
}
