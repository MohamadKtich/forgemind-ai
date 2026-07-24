@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title ForgeMind AI Launcher

if not exist "backend\.venv\Scripts\python.exe" (
  echo ForgeMind is not installed yet. Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
if not exist "frontend\node_modules" (
  echo Frontend packages are missing. Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
if not exist "backend\.env" copy /Y "backend\.env.example" "backend\.env" >nul
if not exist "frontend\.env.local" copy /Y "frontend\.env.example" "frontend\.env.local" >nul

start "ForgeMind Backend" cmd /k ""%~dp0backend\start_backend.bat""
start "ForgeMind Frontend" cmd /k ""%~dp0frontend\start_frontend.bat""

echo Starting ForgeMind AI...
timeout /t 5 /nobreak >nul
start "" http://localhost:3000
exit /b 0
