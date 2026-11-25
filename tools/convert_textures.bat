@echo off
setlocal enabledelayedexpansion
rem Textures: Drezina\data\textures\*.png -> *.paa with ImageToPAA from DayZ Tools.
rem Everything is also written to tools\convert_textures.log
cd /d "%~dp0.."
set "LOG=%~dp0convert_textures.log"
echo convert_textures %date% %time% > "%LOG%"
echo Folder: %CD%
echo Folder: %CD% >> "%LOG%"

set "I2P="
for /f "tokens=2,*" %%A in ('reg query "HKCU\Software\Bohemia Interactive\Dayz Tools" /v path 2^>nul ^| find /i "path"') do set "DZT=%%B"
if defined DZT if exist "!DZT!\Bin\ImageToPAA\ImageToPAA.exe" set "I2P=!DZT!\Bin\ImageToPAA\ImageToPAA.exe"
for %%P in ("%ProgramFiles(x86)%\Steam\steamapps\common\DayZ Tools" "%ProgramFiles%\Steam\steamapps\common\DayZ Tools" "C:\SteamLibrary\steamapps\common\DayZ Tools" "D:\SteamLibrary\steamapps\common\DayZ Tools" "E:\SteamLibrary\steamapps\common\DayZ Tools" "F:\SteamLibrary\steamapps\common\DayZ Tools" "D:\Steam\steamapps\common\DayZ Tools" "E:\Steam\steamapps\common\DayZ Tools") do (
    if not defined I2P if exist "%%~P\Bin\ImageToPAA\ImageToPAA.exe" set "I2P=%%~P\Bin\ImageToPAA\ImageToPAA.exe"
)
if not defined I2P goto noi2p
echo ImageToPAA: !I2P!
echo ImageToPAA: !I2P! >> "%LOG%"

if not exist "Drezina\data\textures\*.png" goto nopng

set /a N=0
set /a BAD=0
for %%F in ("Drezina\data\textures\*.png") do (
    echo   %%~nxF
    echo --- %%~nxF >> "%LOG%"
    "!I2P!" "%%~fF" "%%~dpnF.paa" >> "%LOG%" 2>&1
    if exist "%%~dpnF.paa" (set /a N+=1) else (set /a BAD+=1& echo     FAILED: %%~nxF)
)
echo.
echo DONE: !N! .paa files in Drezina\data\textures, failed: !BAD!
echo DONE: !N! ok, !BAD! failed >> "%LOG%"
echo Log: %LOG%
if not "%~1"=="nopause" pause
exit /b 0

:noi2p
echo ERROR: ImageToPAA not found. Install DayZ Tools in Steam (Library - Tools)
echo or put the path into this file: set "I2P=C:\...\DayZ Tools\Bin\ImageToPAA\ImageToPAA.exe"
echo ERROR: ImageToPAA not found >> "%LOG%"
if not "%~1"=="nopause" pause
exit /b 1

:nopng
echo ERROR: no .png in %CD%\Drezina\data\textures
echo Run this file from the repository folder (the one with tools, Drezina, README.md).
echo ERROR: no png >> "%LOG%"
if not "%~1"=="nopause" pause
exit /b 1
