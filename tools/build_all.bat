@echo off
chcp 65001 >nul
setlocal
rem Всё подряд: модели -> .p3d -> текстуры .paa -> копия на P:\Drezina
cd /d "%~dp0.."
call tools\build_models.bat nopause || goto fail
call tools\convert_textures.bat nopause || goto fail
call tools\copy_to_p.bat nopause || goto fail
echo.
echo ===== ВСЁ ГОТОВО: можно паковать P:\Drezina в Addon Builder =====
pause
exit /b 0
:fail
echo.
echo ===== ОСТАНОВЛЕНО НА ОШИБКЕ, смотрите текст выше =====
pause
exit /b 1
