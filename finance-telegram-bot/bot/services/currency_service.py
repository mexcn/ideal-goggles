"""
Сервис для работы с валютами и курсами
"""
import logging
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional

from ..config import EXCHANGE_API_KEY, EXCHANGE_API_URL, SUPPORTED_CURRENCIES
from ..database import Database

logger = logging.getLogger(__name__)


class CurrencyService:
    """Сервис управления валютами"""
    
    def __init__(self, db: Database):
        self.db = db
        self._cache = {}  # Кэш курсов в памяти
        self._last_update = None
    
    def get_currency_symbol(self, currency_code: str) -> str:
        """Получение символа валюты"""
        return SUPPORTED_CURRENCIES.get(currency_code, {}).get('symbol', currency_code)
    
    def convert(self, amount: float, from_currency: str, to_currency: str) -> float:
        """
        Конвертация суммы из одной валюты в другую
        """
        if from_currency == to_currency:
            return amount
        
        # Получение курсов
        from_rate = self._get_rate_to_usd(from_currency)
        to_rate = self._get_rate_to_usd(to_currency)
        
        if from_rate is None or to_rate is None:
            logger.warning(f"Не удалось получить курсы для {from_currency}->{to_currency}")
            return amount  # Возвращаем исходную сумму если не удалось конвертировать
        
        # Конвертация через USD
        amount_usd = amount / from_rate
        result = amount_usd * to_rate
        
        return round(result, 2)
    
    def _get_rate_to_usd(self, currency_code: str) -> Optional[float]:
        """Получение курса валюты к USD"""
        if currency_code == 'USD':
            return 1.0
        
        # Проверка кэша
        if currency_code in self._cache:
            return self._cache[currency_code]
        
        # Получение из БД
        currency = self.db.get_currency(currency_code)
        if currency:
            rate = currency['rate_to_usd']
            self._cache[currency_code] = rate
            return rate
        
        return None
    
    def update_rates(self) -> bool:
        """
        Обновление курсов валют через API
        """
        if not EXCHANGE_API_KEY:
            logger.warning("EXCHANGE_API_KEY не установлен, используются локальные курсы")
            return False
        
        try:
            # Используем USD как базовую валюту
            url = f"{EXCHANGE_API_URL}/{EXCHANGE_API_KEY}/latest/USD"
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('result') != 'success':
                logger.error(f"Ошибка API: {data.get('error-type')}")
                return False
            
            rates = data.get('conversion_rates', {})
            
            # Обновление курсов в БД
            updated_count = 0
            for currency_code in SUPPORTED_CURRENCIES.keys():
                if currency_code in rates:
                    rate = rates[currency_code]
                    if self.db.update_currency_rate(currency_code, rate):
                        self._cache[currency_code] = rate
                        updated_count += 1
            
            self._last_update = datetime.now()
            logger.info(f"Обновлено курсов: {updated_count}")
            return True
            
        except requests.RequestException as e:
            logger.error(f"Ошибка при обновлении курсов: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при обновлении курсов: {e}")
            return False
    
    def should_update_rates(self, interval_hours: int = 6) -> bool:
        """Проверка необходимости обновления курсов"""
        if self._last_update is None:
            return True
        
        time_since_update = datetime.now() - self._last_update
        return time_since_update > timedelta(hours=interval_hours)
    
    def get_rates_info(self) -> Dict[str, any]:
        """Получение информации о курсах"""
        currencies = self.db.get_all_currencies()
        
        result = {
            'last_update': self._last_update,
            'currencies': {}
        }
        
        for curr in currencies:
            result['currencies'][curr['code']] = {
                'symbol': curr['symbol'],
                'name': curr['name'],
                'rate_to_usd': curr['rate_to_usd'],
                'updated_at': curr['updated_at']
            }
        
        return result
    
    def set_default_rates(self):
        """
        Установка дефолтных курсов (приблизительные значения)
        Используется как fallback если API недоступен
        """
        default_rates = {
            'RUB': 90.0,   # Рублей за доллар
            'USD': 1.0,     # Базовая валюта
            'EUR': 0.92,    # Евро
            'GBP': 0.79,    # Фунт
            'CNY': 7.2,     # Юань
            'KZT': 450.0,   # Тенге
        }
        
        for code, rate in default_rates.items():
            self.db.update_currency_rate(code, rate)
            self._cache[code] = rate
        
        logger.info("Установлены дефолтные курсы валют")
