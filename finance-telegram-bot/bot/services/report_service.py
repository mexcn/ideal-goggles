"""
Сервис для генерации отчетов и графиков
"""
import logging
from datetime import date, timedelta
from typing import Dict, Any, Optional, List
from io import BytesIO
import matplotlib
matplotlib.use('Agg')  # Использование non-GUI backend
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

from ..database import Database
from .expense_service import ExpenseService
from ..config import REPORT_PERIODS
from ..utils.formatters import format_amount, format_date, format_percentage

logger = logging.getLogger(__name__)

# Настройка стиля графиков
sns.set_style("whitegrid")
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['figure.figsize'] = (10, 6)


class ReportService:
    """Сервис генерации отчетов"""
    
    def __init__(self, db: Database, expense_service: ExpenseService):
        self.db = db
        self.expense_service = expense_service
    
    def get_period_dates(self, period: str) -> tuple[date, date]:
        """
        Получение дат начала и конца периода
        """
        today = date.today()
        
        if period == 'week':
            start_date = today - timedelta(days=7)
            end_date = today
        
        elif period == 'month':
            # Первый день текущего месяца до сегодня
            start_date = today.replace(day=1)
            end_date = today
        
        elif period == 'quarter':
            # Последние 3 месяца
            start_date = today - timedelta(days=90)
            end_date = today
        
        elif period == 'year':
            # Первый день года до сегодня
            start_date = today.replace(month=1, day=1)
            end_date = today
        
        else:
            # По умолчанию - месяц
            start_date = today.replace(day=1)
            end_date = today
        
        return start_date, end_date
    
    def generate_text_report(self, user_id: int, period: str = 'month') -> str:
        """
        Генерация текстового отчета
        """
        user = self.db.get_user(user_id)
        if not user:
            return "Ошибка: пользователь не найден"
        
        currency = user['default_currency']
        currency_symbol = self.db.get_currency(currency)['symbol']
        
        start_date, end_date = self.get_period_dates(period)
        
        # Общая сумма расходов
        total = self.expense_service.get_total_expenses(user_id, start_date, end_date)
        
        # Расходы по категориям
        expenses_by_cat = self.expense_service.get_expenses_by_category(
            user_id, start_date, end_date
        )
        
        # Количество дней
        days = (end_date - start_date).days + 1
        avg_per_day = total / days if days > 0 else 0
        
        # Формирование отчета
        lines = []
        lines.append(f"📊 Отчет: {format_date(start_date)} - {format_date(end_date)}\n")
        
        if total == 0:
            lines.append("Нет расходов за этот период")
            return "\n".join(lines)
        
        lines.append(f"💰 Общие расходы: {format_amount(total, currency, True)}\n")
        
        lines.append("📊 По категориям:")
        for cat_name, cat_icon, amount in expenses_by_cat:
            percent = format_percentage(amount, total)
            amount_str = format_amount(amount, currency, False)
            lines.append(f"{cat_icon} {cat_name}: {amount_str} {currency_symbol} ({percent})")
        
        lines.append(f"\n📈 Статистика:")
        lines.append(f"Период: {days} дн.")
        lines.append(f"Средний расход в день: {format_amount(avg_per_day, currency, False)} {currency_symbol}")
        
        # Получение последних расходов
        recent = self.expense_service.get_user_expenses(
            user_id, start_date, end_date, limit=5
        )
        
        if recent:
            lines.append(f"\n🔍 Последние расходы:")
            for exp in recent[:5]:
                exp_date = format_date(exp['expense_date'], 'relative')
                lines.append(
                    f"• {exp['category_icon']} {format_amount(exp['amount_in_default'], currency, False)} "
                    f"{currency_symbol} - {exp['description'] or 'Без описания'} ({exp_date})"
                )
        
        return "\n".join(lines)
    
    def generate_pie_chart(self, user_id: int, period: str = 'month') -> Optional[BytesIO]:
        """
        Генерация круговой диаграммы расходов по категориям
        """
        try:
            user = self.db.get_user(user_id)
            if not user:
                return None
            
            currency = user['default_currency']
            currency_symbol = self.db.get_currency(currency)['symbol']
            
            start_date, end_date = self.get_period_dates(period)
            
            # Получение данных
            expenses_by_cat = self.expense_service.get_expenses_by_category(
                user_id, start_date, end_date
            )
            
            if not expenses_by_cat:
                return None
            
            # Подготовка данных
            categories = []
            amounts = []
            colors = []
            
            for cat_name, cat_icon, amount in expenses_by_cat:
                categories.append(f"{cat_icon} {cat_name}")
                amounts.append(amount)
                
                # Получение цвета категории
                cat = next(
                    (c for c in self.db.get_categories(user_id) if c['name'] == cat_name),
                    None
                )
                colors.append(cat['color'] if cat else '#808080')
            
            # Создание графика
            fig, ax = plt.subplots(figsize=(10, 8))
            
            wedges, texts, autotexts = ax.pie(
                amounts,
                labels=categories,
                autopct='%1.1f%%',
                startangle=90,
                colors=colors,
                textprops={'fontsize': 10}
            )
            
            # Настройка стиля
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontsize(9)
                autotext.set_weight('bold')
            
            ax.set_title(
                f'Расходы по категориям\n{format_date(start_date)} - {format_date(end_date)}',
                fontsize=14,
                weight='bold'
            )
            
            # Легенда с суммами
            legend_labels = [
                f"{cat}: {format_amount(amt, currency, False)} {currency_symbol}"
                for cat, amt in zip(categories, amounts)
            ]
            ax.legend(legend_labels, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
            
            plt.tight_layout()
            
            # Сохранение в BytesIO
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка при генерации круговой диаграммы: {e}")
            return None
    
    def generate_bar_chart(self, user_id: int, period: str = 'month') -> Optional[BytesIO]:
        """
        Генерация столбчатой диаграммы расходов по дням
        """
        try:
            user = self.db.get_user(user_id)
            if not user:
                return None
            
            currency = user['default_currency']
            currency_symbol = self.db.get_currency(currency)['symbol']
            
            start_date, end_date = self.get_period_dates(period)
            
            # Получение всех расходов за период
            expenses = self.expense_service.get_user_expenses(
                user_id, start_date, end_date
            )
            
            if not expenses:
                return None
            
            # Группировка по дням
            df = pd.DataFrame(expenses)
            df['expense_date'] = pd.to_datetime(df['expense_date'])
            daily_expenses = df.groupby('expense_date')['amount_in_default'].sum()
            
            # Создание графика
            fig, ax = plt.subplots(figsize=(12, 6))
            
            daily_expenses.plot(kind='bar', ax=ax, color='#4ECDC4')
            
            ax.set_title(
                f'Расходы по дням\n{format_date(start_date)} - {format_date(end_date)}',
                fontsize=14,
                weight='bold'
            )
            ax.set_xlabel('Дата', fontsize=12)
            ax.set_ylabel(f'Сумма ({currency_symbol})', fontsize=12)
            
            # Форматирование меток оси X
            ax.set_xticklabels(
                [d.strftime('%d.%m') for d in daily_expenses.index],
                rotation=45,
                ha='right'
            )
            
            # Добавление сетки
            ax.grid(axis='y', alpha=0.3)
            
            # Добавление значений на столбцы
            for i, v in enumerate(daily_expenses):
                ax.text(i, v, f'{v:.0f}', ha='center', va='bottom', fontsize=8)
            
            plt.tight_layout()
            
            # Сохранение
            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close()
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка при генерации столбчатой диаграммы: {e}")
            return None
    
    def generate_comparison_report(self, user_id: int, period: str = 'month') -> str:
        """
        Генерация сравнительного отчета с прошлым периодом
        """
        user = self.db.get_user(user_id)
        if not user:
            return "Ошибка: пользователь не найден"
        
        currency = user['default_currency']
        currency_symbol = self.db.get_currency(currency)['symbol']
        
        # Текущий период
        current_start, current_end = self.get_period_dates(period)
        current_total = self.expense_service.get_total_expenses(
            user_id, current_start, current_end
        )
        
        # Прошлый период
        days = (current_end - current_start).days + 1
        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=days - 1)
        previous_total = self.expense_service.get_total_expenses(
            user_id, previous_start, previous_end
        )
        
        # Сравнение
        lines = []
        lines.append(f"📊 Сравнение периодов\n")
        
        lines.append(f"📅 Текущий период:")
        lines.append(f"{format_date(current_start)} - {format_date(current_end)}")
        lines.append(f"Расходы: {format_amount(current_total, currency, True)}\n")
        
        lines.append(f"📅 Прошлый период:")
        lines.append(f"{format_date(previous_start)} - {format_date(previous_end)}")
        lines.append(f"Расходы: {format_amount(previous_total, currency, True)}\n")
        
        # Разница
        if previous_total > 0:
            diff = current_total - previous_total
            diff_percent = (diff / previous_total) * 100
            
            if diff > 0:
                lines.append(f"📈 Увеличение: {format_amount(abs(diff), currency, True)} (+{diff_percent:.1f}%)")
            elif diff < 0:
                lines.append(f"📉 Снижение: {format_amount(abs(diff), currency, True)} ({diff_percent:.1f}%)")
            else:
                lines.append("➡️ Расходы не изменились")
        
        return "\n".join(lines)
    
    def export_to_csv(self, user_id: int, start_date: date, end_date: date) -> Optional[BytesIO]:
        """
        Экспорт данных в CSV
        """
        try:
            expenses = self.expense_service.get_user_expenses(
                user_id, start_date, end_date
            )
            
            if not expenses:
                return None
            
            # Создание DataFrame
            df = pd.DataFrame(expenses)
            
            # Выбор нужных столбцов
            columns = [
                'expense_date', 'category_name', 'amount', 'currency',
                'amount_in_default', 'description'
            ]
            df = df[columns]
            
            # Переименование столбцов
            df.columns = [
                'Дата', 'Категория', 'Сумма', 'Валюта',
                'Сумма в осн. валюте', 'Описание'
            ]
            
            # Сохранение в BytesIO
            buf = BytesIO()
            df.to_csv(buf, index=False, encoding='utf-8-sig')
            buf.seek(0)
            
            return buf
            
        except Exception as e:
            logger.error(f"Ошибка при экспорте в CSV: {e}")
            return None
