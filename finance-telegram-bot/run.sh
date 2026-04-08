#!/bin/bash

# Скрипт запуска Finance Telegram Bot для Linux/macOS

echo "================================"
echo "Finance Telegram Bot"
echo "================================"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    echo "Ошибка: Python 3 не найден"
    echo "Установите Python 3.10 или выше"
    exit 1
fi

# Проверка виртуального окружения
if [ ! -d "venv" ]; then
    echo "Создание виртуального окружения..."
    python3 -m venv venv
fi

# Активация виртуального окружения
echo "Активация виртуального окружения..."
source venv/bin/activate

# Проверка зависимостей
if [ ! -f "venv/installed" ]; then
    echo "Установка зависимостей..."
    pip install -r requirements.txt
    touch venv/installed
fi

# Проверка .env файла
if [ ! -f ".env" ]; then
    echo "Ошибка: Файл .env не найден"
    echo "Скопируйте .env.example в .env и настройте его:"
    echo "  cp .env.example .env"
    exit 1
fi

# Создание необходимых директорий
mkdir -p data/backups
mkdir -p logs

# Запуск бота
echo "Запуск бота..."
echo ""
python -m bot.main

# Деактивация при завершении
deactivate
