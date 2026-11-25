@echo off
chcp 65001 >nul
setlocal
rem Сборка исходников моделей Drezina: сам находит Blender и запускает tools\blender\make_models.py.
rem Запуск: двойной клик по этому файлу (или из PowerShell: .\tools\build_models.bat)
cd /d "%~dp0.."

set "BLENDER="
for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender*") do (
    if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
)
if not defined BLENDER if exist "%ProgramFiles(x86)%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%ProgramFiles(x86)%\Steam\steamapps\common\Blender\blender.exe"
if not defined BLENDER if exist "%ProgramFiles%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%ProgramFiles%\Steam\steamapps\common\Blender\blender.exe"

if not defined BLENDER (
    echo Blender не найден. Установите Blender 4.1 или новее с blender.org
    echo или впишите путь вручную: set "BLENDER=C:\путь\к\blender.exe"
    pause
    exit /b 1
)

echo Blender: %BLENDER%
echo Папка: %CD%
"%BLENDER%" --background --python tools\blender\make_models.py -- build_models
echo.
echo Готово. Модели (.blend и .fbx) лежат в папке build_models
pause
