@echo off
chcp 65001 > nul
REM Скрипт запуска Finance Telegram Bot для Windows

echo ================================
echo Finance Telegram Bot
echo ================================
echo.

REM Проверка Python
python --version >nul 2>&1
if errorlevel 1 (
    echo Ошибка: Python не найден
    echo Установите Python 3.10 или выше
    pause
    exit /b 1
)

REM Проверка виртуального окружения
if not exist "venv" (
    echo Создание виртуального окружения...
    python -m venv venv
)

REM Активация виртуального окружения
echo Активация виртуального окружения...
call venv\Scripts\activate.bat

REM Проверка зависимостей
if not exist "venv\installed" (
    echo Установка зависимостей...
    pip install -r requirements.txt
    echo. > venv\installed
)

REM Проверка .env файла
if not exist ".env" (
    echo Ошибка: Файл .env не найден
    echo Скопируйте .env.example в .env и настройте его:
    echo   copy .env.example .env
    pause
    exit /b 1
)

REM Создание необходимых директорий
if not exist "data\backups" mkdir data\backups
if not exist "logs" mkdir logs

REM Запуск бота
echo Запуск бота...
echo.
python -m bot.main

REM Деактивация при завершении
deactivate
pause
