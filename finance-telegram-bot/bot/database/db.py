"""
Класс для работы с базой данных SQLite
"""
import sqlite3
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path

from ..config import DATABASE_PATH, DEFAULT_CATEGORIES, SUPPORTED_CURRENCIES
from .models import ALL_TABLES, ALL_INDEXES

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        """Инициализация базы данных"""
        self.db_path = db_path
        self._ensure_db_exists()
        self._init_tables()
        self._init_currencies()
    
    def _ensure_db_exists(self):
        """Создание директории для БД если не существует"""
        db_dir = Path(self.db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        """Получение соединения с БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Включаем поддержку внешних ключей
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    
    def _init_tables(self):
        """Создание таблиц если не существуют"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Создание таблиц
                for table_sql in ALL_TABLES:
                    cursor.execute(table_sql)
                
                # Создание индексов
                for index_sql in ALL_INDEXES:
                    cursor.execute(index_sql)
                
                conn.commit()
                logger.info("Таблицы базы данных инициализированы")
        except Exception as e:
            logger.error(f"Ошибка при инициализации таблиц: {e}")
            raise
    
    def _init_currencies(self):
        """Инициализация валют"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                for code, info in SUPPORTED_CURRENCIES.items():
                    cursor.execute(
                        """INSERT OR IGNORE INTO currencies (code, symbol, name, rate_to_usd)
                           VALUES (?, ?, ?, ?)""",
                        (code, info["symbol"], info["name"], 1.0)
                    )
                
                conn.commit()
                logger.info("Валюты инициализированы")
        except Exception as e:
            logger.error(f"Ошибка при инициализации валют: {e}")
    
    # ==================== USERS ====================
    
    def create_user(self, user_id: int, username: Optional[str], first_name: str,
                   default_currency: str = "RUB", timezone: str = "Europe/Moscow") -> bool:
        """Создание нового пользователя"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR IGNORE INTO users 
                       (user_id, username, first_name, default_currency, timezone)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, username, first_name, default_currency, timezone)
                )
                conn.commit()
                
                # Создание категорий по умолчанию
                if cursor.rowcount > 0:
                    self._create_default_categories(user_id)
                    logger.info(f"Создан пользователь {user_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя: {e}")
            return False
    
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение пользователя по ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя: {e}")
            return None
    
    def update_user_currency(self, user_id: int, currency: str) -> bool:
        """Обновление валюты пользователя"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET default_currency = ? WHERE user_id = ?",
                    (currency, user_id)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении валюты: {e}")
            return False
    
    def update_user_activity(self, user_id: int):
        """Обновление времени последней активности пользователя"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,)
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Ошибка при обновлении активности: {e}")
    
    # ==================== CATEGORIES ====================
    
    def _create_default_categories(self, user_id: int):
        """Создание категорий по умолчанию для нового пользователя"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                for category in DEFAULT_CATEGORIES:
                    cursor.execute(
                        """INSERT INTO categories (user_id, name, icon, color)
                           VALUES (?, ?, ?, ?)""",
                        (user_id, category["name"], category["icon"], category["color"])
                    )
                conn.commit()
                logger.info(f"Созданы категории по умолчанию для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при создании категорий: {e}")
    
    def get_categories(self, user_id: int, active_only: bool = True) -> List[Dict[str, Any]]:
        """Получение категорий пользователя"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM categories WHERE user_id = ?"
                params = [user_id]
                
                if active_only:
                    query += " AND is_active = 1"
                
                query += " ORDER BY name"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении категорий: {e}")
            return []
    
    def get_category(self, category_id: int) -> Optional[Dict[str, Any]]:
        """Получение категории по ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении категории: {e}")
            return None
    
    def create_category(self, user_id: int, name: str, icon: str = "📦",
                       color: str = "#808080") -> Optional[int]:
        """Создание новой категории"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO categories (user_id, name, icon, color)
                       VALUES (?, ?, ?, ?)""",
                    (user_id, name, icon, color)
                )
                conn.commit()
                return cursor.lastrowid
        except sqlite3.IntegrityError:
            logger.warning(f"Категория '{name}' уже существует для пользователя {user_id}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при создании категории: {e}")
            return None
    
    def update_category(self, category_id: int, name: Optional[str] = None,
                       icon: Optional[str] = None, color: Optional[str] = None) -> bool:
        """Обновление категории"""
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if icon is not None:
                updates.append("icon = ?")
                params.append(icon)
            if color is not None:
                updates.append("color = ?")
                params.append(color)
            
            if not updates:
                return False
            
            params.append(category_id)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE categories SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении категории: {e}")
            return False
    
    def delete_category(self, category_id: int) -> bool:
        """Удаление категории (мягкое удаление)"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE categories SET is_active = 0 WHERE id = ?",
                    (category_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении категории: {e}")
            return False
    
    # ==================== EXPENSES ====================
    
    def create_expense(self, user_id: int, category_id: int, amount: float,
                      currency: str, amount_in_default: float,
                      description: str = "", expense_date: Optional[date] = None) -> Optional[int]:
        """Создание расхода"""
        try:
            if expense_date is None:
                expense_date = date.today()
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO expenses 
                       (user_id, category_id, amount, currency, amount_in_default, description, expense_date)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (user_id, category_id, amount, currency, amount_in_default, description, expense_date)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании расхода: {e}")
            return None
    
    def get_expenses(self, user_id: int, start_date: Optional[date] = None,
                    end_date: Optional[date] = None, category_id: Optional[int] = None,
                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение расходов пользователя с фильтрацией"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                query = """
                    SELECT e.*, c.name as category_name, c.icon as category_icon
                    FROM expenses e
                    JOIN categories c ON e.category_id = c.id
                    WHERE e.user_id = ?
                """
                params = [user_id]
                
                if start_date:
                    query += " AND e.expense_date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND e.expense_date <= ?"
                    params.append(end_date)
                
                if category_id:
                    query += " AND e.category_id = ?"
                    params.append(category_id)
                
                query += " ORDER BY e.expense_date DESC, e.created_at DESC"
                
                if limit:
                    query += f" LIMIT {limit}"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении расходов: {e}")
            return []
    
    def get_expense(self, expense_id: int) -> Optional[Dict[str, Any]]:
        """Получение расхода по ID"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT e.*, c.name as category_name, c.icon as category_icon
                       FROM expenses e
                       JOIN categories c ON e.category_id = c.id
                       WHERE e.id = ?""",
                    (expense_id,)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении расхода: {e}")
            return None
    
    def update_expense(self, expense_id: int, category_id: Optional[int] = None,
                      amount: Optional[float] = None, description: Optional[str] = None) -> bool:
        """Обновление расхода"""
        try:
            updates = []
            params = []
            
            if category_id is not None:
                updates.append("category_id = ?")
                params.append(category_id)
            if amount is not None:
                updates.append("amount = ?")
                updates.append("amount_in_default = ?")
                params.extend([amount, amount])
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            
            if not updates:
                return False
            
            params.append(expense_id)
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"UPDATE expenses SET {', '.join(updates)} WHERE id = ?",
                    params
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении расхода: {e}")
            return False
    
    def delete_expense(self, expense_id: int) -> bool:
        """Удаление расхода"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении расхода: {e}")
            return False
    
    # ==================== BUDGETS ====================
    
    def create_budget(self, user_id: int, limit_amount: float,
                     category_id: Optional[int] = None, year: Optional[int] = None,
                     month: Optional[int] = None) -> Optional[int]:
        """Создание бюджета"""
        try:
            if year is None:
                now = datetime.now()
                year = now.year
                month = now.month
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT OR REPLACE INTO budgets 
                       (user_id, category_id, limit_amount, year, month)
                       VALUES (?, ?, ?, ?, ?)""",
                    (user_id, category_id, limit_amount, year, month)
                )
                conn.commit()
                return cursor.lastrowid
        except Exception as e:
            logger.error(f"Ошибка при создании бюджета: {e}")
            return None
    
    def get_budget(self, user_id: int, category_id: Optional[int] = None,
                  year: Optional[int] = None, month: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Получение бюджета"""
        try:
            if year is None:
                now = datetime.now()
                year = now.year
                month = now.month
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT * FROM budgets 
                       WHERE user_id = ? AND category_id IS ? AND year = ? AND month = ?""",
                    (user_id, category_id, year, month)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении бюджета: {e}")
            return None
    
    def get_all_budgets(self, user_id: int, year: Optional[int] = None,
                       month: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение всех бюджетов пользователя"""
        try:
            if year is None:
                now = datetime.now()
                year = now.year
                month = now.month
            
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT b.*, c.name as category_name, c.icon as category_icon
                       FROM budgets b
                       LEFT JOIN categories c ON b.category_id = c.id
                       WHERE b.user_id = ? AND b.year = ? AND b.month = ?
                       ORDER BY c.name""",
                    (user_id, year, month)
                )
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении бюджетов: {e}")
            return []
    
    def delete_budget(self, budget_id: int) -> bool:
        """Удаление бюджета"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при удалении бюджета: {e}")
            return False
    
    # ==================== CURRENCIES ====================
    
    def get_currency(self, code: str) -> Optional[Dict[str, Any]]:
        """Получение валюты по коду"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM currencies WHERE code = ?", (code,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении валюты: {e}")
            return None
    
    def get_all_currencies(self) -> List[Dict[str, Any]]:
        """Получение всех валют"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM currencies ORDER BY code")
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Ошибка при получении валют: {e}")
            return []
    
    def update_currency_rate(self, code: str, rate_to_usd: float) -> bool:
        """Обновление курса валюты"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """UPDATE currencies 
                       SET rate_to_usd = ?, updated_at = CURRENT_TIMESTAMP 
                       WHERE code = ?""",
                    (rate_to_usd, code)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении курса валюты: {e}")
            return False
    
    # ==================== STATISTICS ====================
    
    def get_expenses_sum_by_category(self, user_id: int, start_date: date,
                                    end_date: date) -> List[Tuple[str, str, float]]:
        """Получение суммы расходов по категориям за период"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT c.name, c.icon, SUM(e.amount_in_default) as total
                       FROM expenses e
                       JOIN categories c ON e.category_id = c.id
                       WHERE e.user_id = ? AND e.expense_date BETWEEN ? AND ?
                       GROUP BY c.id, c.name, c.icon
                       ORDER BY total DESC""",
                    (user_id, start_date, end_date)
                )
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении суммы по категориям: {e}")
            return []
    
    def get_total_expenses(self, user_id: int, start_date: date, end_date: date) -> float:
        """Получение общей суммы расходов за период"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT SUM(amount_in_default) as total
                       FROM expenses
                       WHERE user_id = ? AND expense_date BETWEEN ? AND ?""",
                    (user_id, start_date, end_date)
                )
                result = cursor.fetchone()
                return result[0] if result[0] else 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении общей суммы расходов: {e}")
            return 0.0
