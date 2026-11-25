@echo off
setlocal
rem Copies the mod folder Drezina (config.cpp, scripts, data, sounds) to P:\Drezina for Addon Builder.
cd /d "%~dp0.."
if not exist P:\ goto nop
if not exist "Drezina\config.cpp" goto norepo
xcopy "Drezina" "P:\Drezina\" /E /I /Y /Q
echo.
echo DONE: P:\Drezina. Next: Addon Builder (step 3).
if not "%~1"=="nopause" pause
exit /b 0

:nop
echo ERROR: drive P: is not mounted. Run DayZ Tools - Workdrive - Mount.
if not "%~1"=="nopause" pause
exit /b 1

:norepo
echo ERROR: Drezina\config.cpp not found in %CD%. Run this file from the repository folder.
if not "%~1"=="nopause" pause
exit /b 1
