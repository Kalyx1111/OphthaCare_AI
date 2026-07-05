@echo off
setlocal EnableDelayedExpansion
title OphthaCare AI - DIAGNOSTIC
mode con: cols=78 lines=55
color 0E
set "BASEDIR=%~dp0"
if "%BASEDIR:~-1%"=="\" set "BASEDIR=%BASEDIR:~0,-1%"
set "VENV_DIR=%BASEDIR%\venv"
set "LOGS_DIR=%BASEDIR%\logs"
set "PORT=5085"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
set "RPT=%LOGS_DIR%\diagnostic_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.txt"
cls
echo.
echo  ================================================================
echo   OphthaCare AI  -  FULL DIAGNOSTIC TOOL
echo  ================================================================
echo.
echo OphthaCare AI Diagnostic > "%RPT%"
echo Date: %DATE% Time: %TIME% >> "%RPT%"
call :SEC "1. INTERNET"
ping -n 1 -w 2000 8.8.8.8 >nul 2>&1
if %errorlevel%==0 (call :OK "Internet: ONLINE") else (call :WARN "Internet: OFFLINE")
call :SEC "2. PYTHON"
python --version >nul 2>&1
if %errorlevel%==0 (for /f "delims=" %%V in ('python --version 2^>^&1') do call :OK "System Python: %%V") else (call :FAIL "System Python: NOT FOUND")
if exist "%VENV_DIR%\Scripts\python.exe" (for /f "delims=" %%V in ('"%VENV_DIR%\Scripts\python.exe" --version 2^>^&1') do call :OK "VEnv Python: %%V") else (call :FAIL "VEnv: NOT CREATED")
call :SEC "3. PACKAGES"
if exist "%VENV_DIR%\Scripts\python.exe" (
    for %%M in (flask flask_cors requests PIL fitz anthropic numpy colorama psutil) do (
        "%VENV_DIR%\Scripts\python.exe" -c "import %%M" >nul 2>&1
        if !errorlevel!==0 (call :OK "  %%M: installed") else (call :FAIL "  %%M: MISSING")
    )
) else (call :WARN "Cannot check - venv not set up")
call :SEC "4. FILES"
for %%F in ("server.py" "static\index.html" "modules\ai_providers.py" "START_OphthaCare_AI.bat") do (
    if exist "%BASEDIR%\%%~F" (for %%S in ("%BASEDIR%\%%~F") do call :OK "  %%~F (%%~zS bytes)") else (call :FAIL "  %%~F MISSING")
)
call :SEC "5. SERVER (port %PORT%)"
netstat -ano 2>nul | findstr ":%PORT% " >nul 2>&1
if %errorlevel%==0 (call :OK "  Server IS running on port %PORT%") else (call :WARN "  Server NOT running")
call :SEC "6. SECURITY"
findstr /C:"SecureKeyStore" "%BASEDIR%\static\index.html" >nul 2>&1
if %errorlevel%==0 (call :OK "  AES-256-GCM key encryption: Present") else (call :WARN "  AES-256-GCM module not found")
call :SEC "7. API PROVIDERS"
if not "%ANTHROPIC_API_KEY%"=="" (call :OK "  ANTHROPIC_API_KEY: Set") else (call :WARN "  No server default key - configure in Settings (5 options available)")
echo.
echo  ================================================================
echo   DIAGNOSTIC COMPLETE - Report: %RPT%
echo  ================================================================
echo.
echo   R = Repair   L = Open Report   S = Start   X = Exit
echo.
:DM
set /p "DC=  Choice [R/L/S/X]: "
if /i "%DC%"=="R" call "%BASEDIR%\REPAIR_AND_RECOVER.bat" & goto :DM
if /i "%DC%"=="L" start notepad "%RPT%" & goto :DM
if /i "%DC%"=="S" call "%BASEDIR%\START_OphthaCare_AI.bat" & exit /b 0
if /i "%DC%"=="X" exit /b 0
goto :DM
:SEC
echo. & echo   --- %~1 --- & echo. >> "%RPT%" & echo --- %~1 --- >> "%RPT%"
goto :EOF
:OK
echo   [ OK ]  %~1 & echo [OK] %~1 >> "%RPT%"
goto :EOF
:WARN
echo   [WARN]  %~1 & echo [WARN] %~1 >> "%RPT%"
goto :EOF
:FAIL
echo   [FAIL]  %~1 & echo [FAIL] %~1 >> "%RPT%"
goto :EOF
