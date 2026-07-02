@echo off
title OphthaCare AI - Stopping Server
color 0C
set "PORT=5085"
echo.
echo  ================================================================
echo   OphthaCare AI  -  STOP SERVER
echo  ================================================================
echo.
echo  Stopping server on port %PORT%...
taskkill /FI "WINDOWTITLE eq OphthaCare AI Server*" /F >nul 2>&1
for /f "tokens=5" %%P in ('netstat -ano 2^>nul ^| findstr ":%PORT% "') do (echo  Stopping PID %%P... & taskkill /PID %%P /F >nul 2>&1)
timeout /t 2 /nobreak >nul
netstat -ano 2>nul | findstr ":%PORT% " >nul 2>&1
if %errorlevel% neq 0 (echo   [ OK ]  OphthaCare AI stopped. Port %PORT% is free.) else (echo   [WARN]  Port may still be in use. Try REPAIR_AND_RECOVER.bat option 5.)
echo.
timeout /t 3 /nobreak >nul
