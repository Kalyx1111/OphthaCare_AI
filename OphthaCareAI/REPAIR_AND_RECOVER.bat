@echo off
setlocal EnableDelayedExpansion
title OphthaCare AI - REPAIR AND RECOVERY
mode con: cols=78 lines=50
color 0C
set "BASEDIR=%~dp0"
if "%BASEDIR:~-1%"=="\" set "BASEDIR=%BASEDIR:~0,-1%"
set "VENV_DIR=%BASEDIR%\venv"
set "LOGS_DIR=%BASEDIR%\logs"
set "OFFLINE_DIR=%BASEDIR%\offline_packages"
set "PYTHON_EXE="
set "ONLINE=false"
if not exist "%LOGS_DIR%" mkdir "%LOGS_DIR%"
set "LOGFILE=%LOGS_DIR%\repair_%DATE:~-4,4%%DATE:~-7,2%%DATE:~-10,2%.log"
cls
echo.
echo  ================================================================
echo   OphthaCare AI  -  REPAIR AND RECOVERY TOOL
echo  ================================================================
echo.
ping -n 1 -w 2000 8.8.8.8 >nul 2>&1
if %errorlevel%==0 (set "ONLINE=true" & echo   [ OK ]  Online) else (set "ONLINE=false" & echo   [ -- ]  Offline)
python --version >nul 2>&1
if %errorlevel%==0 (set "PYTHON_EXE=python" & goto :PY_R)
py --version >nul 2>&1
if %errorlevel%==0 (set "PYTHON_EXE=py" & goto :PY_R)
for %%D in ("%LOCALAPPDATA%\Programs\Python\Python312\python.exe" "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" "C:\Python312\python.exe" "C:\Python311\python.exe") do (if exist %%D (set "PYTHON_EXE=%%~D" & goto :PY_R))
echo   [FAIL]  Python not found.
:PY_R
echo.
echo   1  Rebuild virtual environment
echo   2  Reinstall all packages
echo   3  Recreate missing folders
echo   4  Clear logs and cache
echo   5  Fix port 5085 conflict
echo   6  Run ALL repairs (recommended)
echo   0  Exit
echo.
set /p "CHOICE=  Enter choice (0-6): "
if "%CHOICE%"=="0" exit /b 0
if "%CHOICE%"=="1" goto :VENV
if "%CHOICE%"=="2" goto :PACKAGES
if "%CHOICE%"=="3" goto :FOLDERS
if "%CHOICE%"=="4" goto :LOGS
if "%CHOICE%"=="5" goto :PORT
if "%CHOICE%"=="6" goto :ALL
exit /b 0
:VENV
echo. & echo  Rebuilding venv...
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >> "%LOGFILE%" 2>&1
"%PYTHON_EXE%" -m venv "%VENV_DIR%" >> "%LOGFILE%" 2>&1
if %errorlevel%==0 (echo   [ OK ]  Venv rebuilt.) else (echo   [FAIL]  See: %LOGFILE%)
goto :DONE
:PACKAGES
echo. & echo  Reinstalling packages...
if not exist "%VENV_DIR%\Scripts\pip.exe" ("%PYTHON_EXE%" -m venv "%VENV_DIR%" >> "%LOGFILE%" 2>&1)
set "PIP=%VENV_DIR%\Scripts\pip.exe"
"%PIP%" install --upgrade pip --quiet >> "%LOGFILE%" 2>&1
if "%ONLINE%"=="true" (for %%K in (flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil) do "%PIP%" install %%K --upgrade --quiet >> "%LOGFILE%" 2>&1) else (if exist "%OFFLINE_DIR%\*.whl" ("%PIP%" install flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil --no-index --find-links="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1))
echo   [ OK ]  Packages reinstalled.
goto :DONE
:FOLDERS
echo. & echo  Recreating folders...
for %%D in (uploads offline_packages logs data static reports_db modules) do (if not exist "%BASEDIR%\%%D\" (mkdir "%BASEDIR%\%%D" & echo     Created: %%D) else (echo     OK: %%D))
goto :DONE
:LOGS
echo. & echo  Clearing logs...
if exist "%LOGS_DIR%" del /q "%LOGS_DIR%\*.log" >nul 2>&1 & del /q "%LOGS_DIR%\*.txt" >nul 2>&1
if exist "%BASEDIR%\__pycache__" rmdir /s /q "%BASEDIR%\__pycache__" >nul 2>&1
echo   [ OK ]  Cleared.
goto :DONE
:PORT
echo. & echo  Fixing port 5085...
netstat -ano 2>nul | findstr ":5085 " >nul 2>&1
if %errorlevel%==0 (for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":5085 "') do (echo   Stopping PID %%P... & taskkill /PID %%P /F >nul 2>&1)) & echo   [ OK ]  Port 5085 freed.
goto :DONE
:ALL
echo. & echo  Running all repairs...
netstat -ano 2>nul | findstr ":5085 " >nul 2>&1
if %errorlevel%==0 (for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":5085 "') do taskkill /PID %%P /F >nul 2>&1)
if exist "%VENV_DIR%" rmdir /s /q "%VENV_DIR%" >> "%LOGFILE%" 2>&1
"%PYTHON_EXE%" -m venv "%VENV_DIR%" >> "%LOGFILE%" 2>&1
set "PIP=%VENV_DIR%\Scripts\pip.exe"
"%PIP%" install --upgrade pip --quiet >> "%LOGFILE%" 2>&1
if "%ONLINE%"=="true" ("%PIP%" install flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil --quiet >> "%LOGFILE%" 2>&1) else (if exist "%OFFLINE_DIR%\*.whl" ("%PIP%" install flask flask-cors requests Pillow PyMuPDF anthropic numpy python-docx colorama psutil --no-index --find-links="%OFFLINE_DIR%" --quiet >> "%LOGFILE%" 2>&1))
for %%D in (uploads offline_packages logs data static reports_db modules) do if not exist "%BASEDIR%\%%D\" mkdir "%BASEDIR%\%%D" >nul 2>&1
if exist "%LOGS_DIR%" del /q "%LOGS_DIR%\*.log" >nul 2>&1
echo   [ OK ]  All repairs done.
goto :DONE
:DONE
echo.
echo  ================================================================
echo   Complete. Log: %LOGFILE%
echo  ================================================================
echo.
set /p "POST=  S=Start  D=Diagnostic  X=Exit: "
if /i "%POST%"=="S" call "%BASEDIR%\START_OphthaCare_AI.bat"
if /i "%POST%"=="D" call "%BASEDIR%\DIAGNOSTIC.bat"
exit /b 0
