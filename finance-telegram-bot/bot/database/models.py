"""
SQL схемы таблиц базы данных
"""

# Таблица пользователей
USERS_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    default_currency TEXT DEFAULT 'RUB',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    timezone TEXT DEFAULT 'Europe/Moscow'
)
"""

# Таблица расходов
EXPENSES_TABLE = """
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    currency TEXT DEFAULT 'RUB',
    amount_in_default REAL NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expense_date DATE NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
)
"""

# Индексы для таблицы расходов
EXPENSES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_date ON expenses(user_id, expense_date)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_category ON expenses(category_id)",
    "CREATE INDEX IF NOT EXISTS idx_expenses_user_id ON expenses(user_id)",
]

# Таблица категорий расходов
CATEGORIES_TABLE = """
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    icon TEXT DEFAULT '📦',
    color TEXT DEFAULT '#808080',
    is_active BOOLEAN DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    UNIQUE(user_id, name)
)
"""

# Индекс для категорий
CATEGORIES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_categories_user ON categories(user_id)",
]

# Таблица бюджетов
BUDGETS_TABLE = """
CREATE TABLE IF NOT EXISTS budgets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    category_id INTEGER,
    limit_amount REAL NOT NULL,
    period TEXT DEFAULT 'month',
    year INTEGER NOT NULL,
    month INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE,
    UNIQUE(user_id, category_id, year, month)
)
"""

# Индексы для бюджетов
BUDGETS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_budgets_user ON budgets(user_id)",
    "CREATE INDEX IF NOT EXISTS idx_budgets_period ON budgets(year, month)",
]

# Таблица валют
CURRENCIES_TABLE = """
CREATE TABLE IF NOT EXISTS currencies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    rate_to_usd REAL NOT NULL DEFAULT 1.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# Все таблицы и индексы
ALL_TABLES = [
    USERS_TABLE,
    EXPENSES_TABLE,
    CATEGORIES_TABLE,
    BUDGETS_TABLE,
    CURRENCIES_TABLE,
]

ALL_INDEXES = (
    EXPENSES_INDEXES +
    CATEGORIES_INDEXES +
    BUDGETS_INDEXES
)
