@echo off
setlocal
rem Step 2: models -> .blend (build_models) -> .p3d (Drezina\data). Run from the repository folder.
cd /d "%~dp0.."
set "BLENDER="
for /d %%D in ("%ProgramFiles%\Blender Foundation\Blender*") do (
    if exist "%%D\blender.exe" set "BLENDER=%%D\blender.exe"
)
if not defined BLENDER if exist "%ProgramFiles(x86)%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%ProgramFiles(x86)%\Steam\steamapps\common\Blender\blender.exe"
if not defined BLENDER if exist "%ProgramFiles%\Steam\steamapps\common\Blender\blender.exe" set "BLENDER=%ProgramFiles%\Steam\steamapps\common\Blender\blender.exe"
if not defined BLENDER goto noblender
echo Blender: %BLENDER%

echo.
echo [1/2] Building models...
"%BLENDER%" --background --python tools\blender\make_models.py -- build_models
if errorlevel 1 goto fail
echo.
echo [2/2] Writing .p3d to Drezina\data ...
"%BLENDER%" --background --python tools\blender\export_p3d.py -- build_models Drezina\data
if errorlevel 1 goto fail
echo.
echo DONE: .p3d models are in Drezina\data
if not "%~1"=="nopause" pause
exit /b 0

:noblender
echo ERROR: Blender not found. Install Blender 4.1+ from blender.org
echo or put the path into this file: set "BLENDER=C:\path\to\blender.exe"
if not "%~1"=="nopause" pause
exit /b 1

:fail
echo ERROR while building models, see the text above.
if not "%~1"=="nopause" pause
exit /b 1
