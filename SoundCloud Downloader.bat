@echo off
chcp 65001 >nul
title SoundCloud Downloader
echo ========================================================
echo   SoundCloud Downloader for Windows
echo ========================================================
echo.

where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ОШИБКА] Python не обнаружен в вашей системе!
    echo Скачайте и установите Python с https://www.python.org/downloads/
    echo (Обязательно поставьте галочку "Add Python to PATH" при установке).
    echo.
    pause
    exit /b 1
)

echo Проверка зависимостей...
python -m pip install -q -r requirements.txt
python -m pip install -q pywebview

echo Запуск приложения...
python app_windows.py
