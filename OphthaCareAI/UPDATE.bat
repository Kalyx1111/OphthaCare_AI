@echo off
setlocal EnableDelayedExpansion
title OphthaCare AI - UPDATE
mode con: cols=78 lines=40
color 0A
set "BASEDIR=%~dp0"
if "%BASEDIR:~-1%"=="\" set "BASEDIR=%BASEDIR:~0,-1%"
set "VENV_DIR=%BASEDIR%\venv"
set "OFFLINE_DIR=%BASEDIR%\offline_packages"
set "LOGS_DIR=%BASEDIR%\logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
set "LOGFILE=%LOGS_DIR%\update_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log"
cls
echo.
echo  ================================================================
echo   OphthaCare AI  -  UPDATE TOOL
echo  ================================================================
echo.
ping -n 1 -w 2000 8.8.8.8 >nul 2>&1
if %errorlevel% neq 0 (echo   [FAIL]  No internet. & pause & exit /b 1)
if not exist "%VENV_DIR%\Scripts\pip.exe" (echo   [FAIL]  Venv not found. Run START_OphthaCare_AI.bat first. & pause & exit /b 1)
set "PIP=%VENV_DIR%\Scripts\pip.exe"
echo   1  Update all packages
echo   2  Update + refresh offline cache
echo   3  Check for outdated packages
echo   0  Cancel
echo.
set /p "CHOICE=  Choice (0-3): "
if "%CHOICE%"=="0" exit /b 0
if "%CHOICE%"=="3" (echo. & "%PIP%" list --outdated & pause & exit /b 0)
echo.
"%PIP%" install --upgrade pip --quiet >> "%LOGFILE%" 2>&1
for %%K in (flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil) do (
    echo     Upgrading %%K...
    "%PIP%" install --upgrade %%K --quiet >> "%LOGFILE%" 2>&1
    if "%CHOICE%"=="2" ("%PIP%" download %%K --dest="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1)
)
echo   [ OK ]  All packages updated.
echo.
echo  Restart OphthaCare AI to apply updates.
echo.
pause
