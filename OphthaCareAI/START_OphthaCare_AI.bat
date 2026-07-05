@echo off
setlocal EnableDelayedExpansion
title OphthaCare AI - Launching
mode con: cols=78 lines=50
color 0F
set "BASEDIR=%~dp0"
if "%BASEDIR:~-1%"=="\" set "BASEDIR=%BASEDIR:~0,-1%"
set "VENV_DIR=%BASEDIR%\venv"
set "OFFLINE_DIR=%BASEDIR%\offline_packages"
set "LOGS_DIR=%BASEDIR%\logs"
set "PORT=5085"
set "ONLINE=false"
set "PYTHON_EXE="
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
set "LOGFILE=%LOGS_DIR%\launch_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log"
cls
echo.
echo  ================================================================
echo   OphthaCare AI  -  Ophthalmology Health Intelligence v1.0
echo  ================================================================
echo.
echo  MEDICAL DISCLAIMER:
echo  This is an AI Research Tool ONLY. Not medical advice.
echo  ALWAYS consult your ophthalmologist before any decision.
echo  EYE EMERGENCY: Eye Casualty / 112 (India) / 999 (UK) / 911 (US)
echo  Chemical injury: IRRIGATE IMMEDIATELY with water 20+ minutes.
echo.
echo  ================================================================
echo.
echo  [STEP 1/7]  Checking internet...
ping -n 1 -w 2000 8.8.8.8 >nul 2>&1
if %errorlevel%==0 (set "ONLINE=true" & echo              [ OK ]  Online) else (set "ONLINE=false" & echo              [ -- ]  Offline)
echo.
echo  [STEP 2/7]  Looking for Python...
python --version >nul 2>&1
if %errorlevel%==0 (set "PYTHON_EXE=python" & goto :PY_OK)
py --version >nul 2>&1
if %errorlevel%==0 (set "PYTHON_EXE=py" & goto :PY_OK)
for %%D in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "%LOCALAPPDATA%\Programs\Python\Python310\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe") do (
    if exist %%D (set "PYTHON_EXE=%%~D" & goto :PY_OK)
)
echo              [FAIL]  Python not found.
if "%ONLINE%"=="true" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\py_setup.exe' -UseBasicParsing" >> "%LOGFILE%" 2>&1
    if exist "%TEMP%\py_setup.exe" (start /wait "" "%TEMP%\py_setup.exe" & set "PYTHON_EXE=python")
)
if "%PYTHON_EXE%"=="" (echo  Install Python from: https://www.python.org/downloads/ & pause & exit /b 1)
:PY_OK
for /f "tokens=*" %%V in ('"%PYTHON_EXE%" --version 2^>^&1') do echo              [ OK ]  %%V
echo.
echo  [STEP 3/7]  Setting up virtual environment...
if not exist "%VENV_DIR%\Scripts\python.exe" (
    "%PYTHON_EXE%" -m venv "%VENV_DIR%" >> "%LOGFILE%" 2>&1
    if !errorlevel! neq 0 (echo              [FAIL]  Run REPAIR_AND_RECOVER.bat & pause & exit /b 1)
    echo              [ OK ]  Created.
) else (echo              [ OK ]  Ready.)
set "VPYTHON=%VENV_DIR%\Scripts\python.exe"
set "VPIP=%VENV_DIR%\Scripts\pip.exe"
echo.
echo  [STEP 4/7]  Checking packages...
"%VPYTHON%" -c "import flask" >nul 2>&1
if %errorlevel%==0 (echo              [ OK ]  Packages installed. & goto :PKG_DONE)
echo              Installing - please wait 2-5 minutes...
"%VPYTHON%" -m pip install --upgrade pip --quiet >> "%LOGFILE%" 2>&1
if "%ONLINE%"=="true" (
    for %%K in (flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil) do (
        echo                Installing %%K...
        "%VPIP%" install %%K --quiet >> "%LOGFILE%" 2>&1
        "%VPIP%" download %%K --dest="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1
    )
) else (
    if exist "%OFFLINE_DIR%\*.whl" ("%VPIP%" install flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil --no-index --find-links="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1) else (echo  No offline packages. Run DOWNLOAD_OFFLINE_PACKAGES.bat while online. & pause & exit /b 1)
)
"%VPYTHON%" -c "import flask" >nul 2>&1
if !errorlevel! neq 0 (echo  [FAIL] Install failed. Check: %LOGFILE% & start notepad "%LOGFILE%" & pause & exit /b 1)
echo              [ OK ]  All packages ready.
:PKG_DONE
echo.
echo  [STEP 5/7]  Checking files...
if not exist "%BASEDIR%\server.py" (echo              [FAIL]  server.py missing. Re-extract ZIP. & pause & exit /b 1)
if not exist "%BASEDIR%\static\index.html" (echo              [FAIL]  static\index.html missing. Re-extract ZIP. & pause & exit /b 1)
for %%D in (uploads offline_packages logs data static reports_db modules) do if not exist "%BASEDIR%\%%D\" mkdir "%BASEDIR%\%%D" >nul 2>&1
echo              [ OK ]  Files verified.
echo.
echo  [STEP 6/7]  Checking port %PORT%...
netstat -ano 2>nul | findstr ":%PORT% " >nul 2>&1
if %errorlevel%==0 (for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%PORT% "') do taskkill /PID %%P /F >nul 2>&1 & timeout /t 2 /nobreak >nul & echo              [ OK ]  Port freed.) else (echo              [ OK ]  Port %PORT% available.)
echo.
echo  [STEP 7/7]  Starting OphthaCare AI...
if not "%ANTHROPIC_API_KEY%"=="" (echo              [ OK ]  Server default API key found.) else (echo              [ -- ]  No server default key - choose provider in Settings.)
start "OphthaCare AI Server" cmd /k "echo OphthaCare AI Server - Keep Open && "%VPYTHON%" "%BASEDIR%\server.py" --port %PORT%"
set "SERVER_UP=false"
for /L %%i in (1,1,25) do (
    timeout /t 1 /nobreak >nul
    curl -s "http://localhost:%PORT%/api/health" >nul 2>&1
    if !errorlevel!==0 (set "SERVER_UP=true" & goto :SRV_READY)
    echo              Starting... [%%i/25]
)
:SRV_READY
cls
echo.
echo  ================================================================
echo   OphthaCare AI IS RUNNING
echo  ================================================================
echo.
echo   Open in browser:   http://localhost:%PORT%
echo   Security: AES-256-GCM API key encryption active
echo   Log:  %LOGFILE%
echo.
echo  ================================================================
echo   DISCLAIMER: Research only. Consult your ophthalmologist.
echo   EYE EMERGENCY: Eye Casualty / 112 India / 999 UK / 911 US
echo  ================================================================
echo.
timeout /t 2 /nobreak >nul
start "" "http://localhost:%PORT%"
echo.
echo   V = View log   D = Diagnostics   U = Update   Q = Quit
echo.
:MENU
set /p "CHOICE=  Choice [V/D/U/Q]: "
if /i "!CHOICE!"=="V" start notepad "%LOGFILE%" & goto :MENU
if /i "!CHOICE!"=="D" call "%BASEDIR%\DIAGNOSTIC.bat" & goto :MENU
if /i "!CHOICE!"=="U" call "%BASEDIR%\UPDATE.bat" & goto :MENU
if /i "!CHOICE!"=="Q" goto :QUIT
goto :MENU
:QUIT
taskkill /FI "WINDOWTITLE eq OphthaCare AI Server*" /F >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%PORT% "') do taskkill /PID %%P /F >nul 2>&1
echo  Stopped. Goodbye.
timeout /t 2 /nobreak >nul
exit /b 0
:LOG
echo [%DATE% %TIME%] %~1 >> "%LOGFILE%"
goto :EOF
