@echo off
chcp 65001 >nul
setlocal
rem Шаг 2 целиком: модели -> .blend (build_models) -> .p3d (Drezina\data). Object Builder не нужен.
rem Запускать из папки репозитория (двойной клик по файлу), а не с диска P:.
cd /d "%~dp0.."
set "BLENDER="
for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender*") do (
    if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
)
if not defined BLENDER if exist "%ProgramFiles(x86)%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%ProgramFiles(x86)%\Steam\steamapps\common\Blender\blender.exe"
if not defined BLENDER if exist "%ProgramFiles%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%ProgramFiles%\Steam\steamapps\common\Blender\blender.exe"
if not defined BLENDER (
    echo Blender не найден. Установите Blender 4.1 или новее с blender.org
    echo или впишите путь вручную в этот файл: set "BLENDER=C:\путь\к\blender.exe"
    pause
    exit /b 1
)
echo Blender: %BLENDER%

echo.
echo [1/2] Строю модели...
"%BLENDER%" --background --python tools\blender\make_models.py -- build_models
if errorlevel 1 goto fail
echo.
echo [2/2] Записываю .p3d в Drezina\data ...
"%BLENDER%" --background --python tools\blender\export_p3d.py -- build_models Drezina\data
if errorlevel 1 goto fail
echo.
echo Готово: модели .p3d лежат в Drezina\data
if not "%~1"=="nopause" pause
exit /b 0
:fail
echo ОШИБКА при сборке моделей, смотрите текст выше.
if not "%~1"=="nopause" pause
exit /b 1
