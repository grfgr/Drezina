@echo off
setlocal
rem Everything: models -> .p3d -> textures .paa -> copy to P:\Drezina
cd /d "%~dp0.."
call tools\build_models.bat nopause || goto fail
call tools\convert_textures.bat nopause || goto fail
call tools\copy_to_p.bat nopause || goto fail
echo.
echo ===== ALL DONE: pack P:\Drezina with Addon Builder =====
pause
exit /b 0
:fail
echo.
echo ===== STOPPED ON ERROR, see the text above =====
pause
exit /b 1
