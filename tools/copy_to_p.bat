@echo off
chcp 65001 >nul
setlocal
rem Копирует папку мода Drezina (config.cpp, scripts, data, sounds) на P:\Drezina для Addon Builder.
cd /d "%~dp0.."
if not exist P:\ (
    echo Диск P: не смонтирован. Запустите DayZ Tools - Workdrive - Mount.
    if not "%~1"=="nopause" pause
    exit /b 1
)
xcopy "Drezina" "P:\Drezina\" /E /I /Y /Q
echo.
echo Готово: P:\Drezina. Дальше — Addon Builder (шаг 3 инструкции).
if not "%~1"=="nopause" pause
