"""
Сервис для работы с бюджетами
"""
import logging
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from calendar import monthrange

from ..database import Database
from .expense_service import ExpenseService

logger = logging.getLogger(__name__)


class BudgetService:
    """Сервис управления бюджетом"""
    
    def __init__(self, db: Database, expense_service: ExpenseService):
        self.db = db
        self.expense_service = expense_service
    
    def set_budget(self, user_id: int, limit_amount: float,
                  category_id: Optional[int] = None, year: Optional[int] = None,
                  month: Optional[int] = None) -> Optional[int]:
        """Установка бюджета для категории или общего бюджета"""
        if year is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        budget_id = self.db.create_budget(
            user_id=user_id,
            limit_amount=limit_amount,
            category_id=category_id,
            year=year,
            month=month
        )
        
        if budget_id:
            category_name = "Общий" if category_id is None else "категории"
            logger.info(f"Установлен бюджет {budget_id} ({category_name}) для пользователя {user_id}")
        
        return budget_id
    
    def get_budget(self, user_id: int, category_id: Optional[int] = None,
                  year: Optional[int] = None, month: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """Получение бюджета"""
        return self.db.get_budget(user_id, category_id, year, month)
    
    def get_all_budgets(self, user_id: int, year: Optional[int] = None,
                       month: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получение всех бюджетов пользователя"""
        return self.db.get_all_budgets(user_id, year, month)
    
    def delete_budget(self, budget_id: int) -> bool:
        """Удаление бюджета"""
        return self.db.delete_budget(budget_id)
    
    def check_budget(self, user_id: int, category_id: Optional[int] = None,
                    year: Optional[int] = None, month: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        Проверка статуса бюджета
        Возвращает информацию о бюджете, потраченной сумме и остатке
        """
        if year is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        # Получение бюджета
        budget = self.get_budget(user_id, category_id, year, month)
        if not budget:
            return None
        
        # Расчет периода
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)
        
        # Получение потраченной суммы
        if category_id is None:
            # Общий бюджет
            spent = self.expense_service.get_total_expenses(user_id, start_date, end_date)
        else:
            # Бюджет категории
            spent = self.expense_service.get_category_expenses(
                user_id, category_id, start_date, end_date
            )
        
        limit = budget['limit_amount']
        remaining = limit - spent
        percent = (spent / limit * 100) if limit > 0 else 0
        
        return {
            'budget': budget,
            'spent': spent,
            'remaining': remaining,
            'limit': limit,
            'percent': percent,
            'start_date': start_date,
            'end_date': end_date,
        }
    
    def check_budget_after_expense(self, user_id: int, category_id: int,
                                  expense_amount: float) -> Tuple[bool, Optional[str]]:
        """
        Проверка бюджета после добавления расхода
        Возвращает (exceeded, warning_message)
        """
        now = datetime.now()
        
        # Проверка бюджета категории
        budget_status = self.check_budget(user_id, category_id, now.year, now.month)
        
        if budget_status:
            percent = budget_status['percent']
            category = self.db.get_category(category_id)
            category_name = category['name'] if category else 'категории'
            
            if percent >= 100:
                message = f"🚨 Бюджет категории \"{category_name}\" превышен!\n"
                message += f"Лимит: {budget_status['limit']:.2f}\n"
                message += f"Потрачено: {budget_status['spent']:.2f}"
                return True, message
            
            elif percent >= 80:
                message = f"⚠️ Использовано {percent:.1f}% бюджета категории \"{category_name}\"\n"
                message += f"Осталось: {budget_status['remaining']:.2f}"
                return False, message
        
        # Проверка общего бюджета
        general_budget = self.check_budget(user_id, None, now.year, now.month)
        
        if general_budget:
            percent = general_budget['percent']
            
            if percent >= 100:
                message = f"🚨 Общий бюджет превышен!\n"
                message += f"Лимит: {general_budget['limit']:.2f}\n"
                message += f"Потрачено: {general_budget['spent']:.2f}"
                return True, message
            
            elif percent >= 80:
                message = f"⚠️ Использовано {percent:.1f}% общего бюджета\n"
                message += f"Осталось: {general_budget['remaining']:.2f}"
                return False, message
        
        return False, None
    
    def get_budget_summary(self, user_id: int, year: Optional[int] = None,
                          month: Optional[int] = None) -> Dict[str, Any]:
        """
        Получение сводки по всем бюджетам
        """
        if year is None:
            now = datetime.now()
            year = now.year
            month = now.month
        
        budgets = self.get_all_budgets(user_id, year, month)
        
        summary = {
            'total_limit': 0.0,
            'total_spent': 0.0,
            'budgets': []
        }
        
        for budget in budgets:
            category_id = budget.get('category_id')
            status = self.check_budget(user_id, category_id, year, month)
            
            if status:
                summary['total_limit'] += status['limit']
                summary['total_spent'] += status['spent']
                summary['budgets'].append(status)
        
        summary['total_remaining'] = summary['total_limit'] - summary['total_spent']
        summary['total_percent'] = (
            (summary['total_spent'] / summary['total_limit'] * 100)
            if summary['total_limit'] > 0 else 0
        )
        
        return summary
    
    def forecast_expenses(self, user_id: int, category_id: Optional[int] = None) -> Optional[float]:
        """
        Прогнозирование расходов до конца месяца на основе текущих трат
        """
        now = datetime.now()
        year = now.year
        month = now.month
        current_day = now.day
        
        # Количество дней в месяце
        days_in_month = monthrange(year, month)[1]
        
        # Период с начала месяца
        start_date = date(year, month, 1)
        today = date.today()
        
        # Получение расходов за текущий период
        if category_id is None:
            spent = self.expense_service.get_total_expenses(user_id, start_date, today)
        else:
            spent = self.expense_service.get_category_expenses(
                user_id, category_id, start_date, today
            )
        
        if spent == 0 or current_day == 0:
            return 0.0
        
        # Средний расход в день
        avg_per_day = spent / current_day
        
        # Прогноз на оставшиеся дни
        remaining_days = days_in_month - current_day
        forecast_remaining = avg_per_day * remaining_days
        
        # Общий прогноз
        total_forecast = spent + forecast_remaining
        
        return round(total_forecast, 2)
