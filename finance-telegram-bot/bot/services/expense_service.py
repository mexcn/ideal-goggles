"""
Сервис для работы с расходами
"""
import logging
from datetime import date, datetime
from typing import Optional, List, Dict, Any

from ..database import Database
from .currency_service import CurrencyService

logger = logging.getLogger(__name__)


class ExpenseService:
    """Сервис управления расходами"""
    
    def __init__(self, db: Database, currency_service: CurrencyService):
        self.db = db
        self.currency_service = currency_service
    
    def add_expense(self, user_id: int, category_id: int, amount: float,
                   currency: Optional[str] = None, description: str = "",
                   expense_date: Optional[date] = None) -> Optional[int]:
        """
        Добавление расхода с автоматической конвертацией валюты
        """
        # Получение валюты пользователя по умолчанию
        user = self.db.get_user(user_id)
        if not user:
            logger.error(f"Пользователь {user_id} не найден")
            return None
        
        default_currency = user['default_currency']
        
        # Если валюта не указана, используем валюту по умолчанию
        if currency is None:
            currency = default_currency
        
        # Конвертация в валюту по умолчанию если нужно
        amount_in_default = self.currency_service.convert(
            amount, currency, default_currency
        )
        
        # Создание расхода
        expense_id = self.db.create_expense(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            currency=currency,
            amount_in_default=amount_in_default,
            description=description,
            expense_date=expense_date or date.today()
        )
        
        if expense_id:
            logger.info(f"Добавлен расход {expense_id} для пользователя {user_id}")
        
        return expense_id
    
    def get_expense(self, expense_id: int) -> Optional[Dict[str, Any]]:
        """Получение расхода по ID"""
        return self.db.get_expense(expense_id)
    
    def get_user_expenses(self, user_id: int, start_date: Optional[date] = None,
                         end_date: Optional[date] = None, category_id: Optional[int] = None,
                         limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение расходов пользователя с фильтрацией"""
        return self.db.get_expenses(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date,
            category_id=category_id,
            limit=limit
        )
    
    def get_recent_expenses(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Получение последних расходов пользователя"""
        return self.db.get_expenses(user_id=user_id, limit=limit)
    
    def update_expense(self, expense_id: int, category_id: Optional[int] = None,
                      amount: Optional[float] = None, description: Optional[str] = None) -> bool:
        """Обновление расхода"""
        return self.db.update_expense(
            expense_id=expense_id,
            category_id=category_id,
            amount=amount,
            description=description
        )
    
    def delete_expense(self, expense_id: int) -> bool:
        """Удаление расхода"""
        return self.db.delete_expense(expense_id)
    
    def get_total_expenses(self, user_id: int, start_date: date, end_date: date) -> float:
        """Получение общей суммы расходов за период"""
        return self.db.get_total_expenses(user_id, start_date, end_date)
    
    def get_expenses_by_category(self, user_id: int, start_date: date,
                                end_date: date) -> List[tuple]:
        """Получение расходов сгруппированных по категориям"""
        return self.db.get_expenses_sum_by_category(user_id, start_date, end_date)
    
    def get_category_expenses(self, user_id: int, category_id: int,
                            start_date: date, end_date: date) -> float:
        """Получение суммы расходов по категории за период"""
        expenses = self.db.get_expenses(
            user_id=user_id,
            category_id=category_id,
            start_date=start_date,
            end_date=end_date
        )
        
        return sum(exp['amount_in_default'] for exp in expenses)
