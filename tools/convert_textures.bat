@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion
rem Шаг текстур: Drezina\data\textures\*.png -> *.paa через ImageToPAA из DayZ Tools.
cd /d "%~dp0.."

set "I2P="
rem путь к DayZ Tools из реестра (его пишет Steam при установке)
for /f "tokens=2,*" %%A in ('reg query "HKCU\Software\Bohemia Interactive\Dayz Tools" /v path 2^>nul ^| find /i "path"') do set "DZT=%%B"
if defined DZT if exist "!DZT!\Bin\ImageToPAA\ImageToPAA.exe" set "I2P=!DZT!\Bin\ImageToPAA\ImageToPAA.exe"
for %%P in ("%ProgramFiles(x86)%\Steam\steamapps\common\DayZ Tools" "%ProgramFiles%\Steam\steamapps\common\DayZ Tools" "C:\SteamLibrary\steamapps\common\DayZ Tools" "D:\SteamLibrary\steamapps\common\DayZ Tools" "E:\SteamLibrary\steamapps\common\DayZ Tools" "F:\SteamLibrary\steamapps\common\DayZ Tools") do (
    if not defined I2P if exist "%%~P\Bin\ImageToPAA\ImageToPAA.exe" set "I2P=%%~P\Bin\ImageToPAA\ImageToPAA.exe"
)
if not defined I2P (
    echo ImageToPAA не найден. Установите DayZ Tools в Steam ^(Библиотека - Инструменты^)
    echo или впишите путь вручную в этот файл: set "I2P=C:\...\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe"
    if not "%~1"=="nopause" pause
    exit /b 1
)
echo ImageToPAA: !I2P!
echo.

set /a N=0
for %%F in ("Drezina\data\textures\*.png") do (
    echo   %%~nxF
    "!I2P!" "%%~fF" "%%~dpnF.paa" >nul
    if exist "%%~dpnF.paa" (set /a N+=1) else (echo     ОШИБКА: не получилось)
)
echo.
echo Готово: !N! текстур .paa в Drezina\data\textures
if not "%~1"=="nopause" pause
exit /b 0
