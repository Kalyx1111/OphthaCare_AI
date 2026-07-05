@echo off
setlocal EnableDelayedExpansion
title OphthaCare AI - Download Offline Packages
mode con: cols=78 lines=40
color 0B
set "BASEDIR=%~dp0"
if "%BASEDIR:~-1%"=="\" set "BASEDIR=%BASEDIR:~0,-1%"
set "OFFLINE_DIR=%BASEDIR%\offline_packages"
set "VENV_DIR=%BASEDIR%\venv"
set "LOGS_DIR=%BASEDIR%\logs"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
if not exist "%OFFLINE_DIR%" mkdir "%OFFLINE_DIR%"
set "LOGFILE=%LOGS_DIR%\offline_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log"
cls
echo.
echo  ================================================================
echo   OphthaCare AI  -  OFFLINE PACKAGE DOWNLOADER
echo  ================================================================
echo.
ping -n 1 -w 3000 8.8.8.8 >nul 2>&1
if %errorlevel% neq 0 (echo   [FAIL]  No internet. Connect and try again. & pause & exit /b 1)
echo   [ OK ]  Internet connected.
set "PIP="
if exist "%VENV_DIR%\Scripts\pip.exe" (set "PIP=%VENV_DIR%\Scripts\pip.exe") else (pip --version >nul 2>&1 && set "PIP=pip")
if "%PIP%"=="" (echo   [FAIL]  pip not found. Run START_OphthaCare_AI.bat first. & pause & exit /b 1)
%PIP% install --upgrade pip --quiet >> "%LOGFILE%" 2>&1
echo  Downloading packages (3-8 minutes)...
set /a DONE=0
for %%K in (flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil) do (
    set /a DONE+=1
    echo   [!DONE!/10]  Downloading: %%K
    %PIP% download %%K --dest="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1
)
set /a WHLCOUNT=0
for %%W in ("%OFFLINE_DIR%\*.whl") do set /a WHLCOUNT+=1
echo.
echo   [ OK ]  %WHLCOUNT% packages cached.
echo.
echo  ================================================================
echo   DOWNLOAD COMPLETE. OphthaCare AI now works WITHOUT internet.
echo  ================================================================
echo.
pause
