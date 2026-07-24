@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title ForgeMind AI Setup

echo =====================================================
echo   ForgeMind AI - First Installation
echo =====================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python was not found.
  echo Install Python 3.11 or newer, enable "Add Python to PATH", then run this file again.
  pause
  exit /b 1
)

where node >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Node.js was not found.
  echo Install Node.js 22 LTS or newer, then run this file again.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm was not found. Reinstall Node.js 22 LTS.
  pause
  exit /b 1
)

echo [1/5] Creating the Python environment...
if not exist "backend\.venv\Scripts\python.exe" python -m venv "backend\.venv"
if errorlevel 1 goto :failed

echo [2/5] Installing backend dependencies...
call "backend\.venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r "backend\requirements.txt"
if errorlevel 1 goto :failed

echo [3/5] Creating local environment files...
if not exist "backend\.env" copy /Y "backend\.env.example" "backend\.env" >nul
if not exist "frontend\.env.local" copy /Y "frontend\.env.example" "frontend\.env.local" >nul

echo [4/5] Installing frontend dependencies...
pushd frontend
call npm ci
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo [5/5] Verifying the backend and frontend...
pushd backend
call ".venv\Scripts\activate.bat"
python -m pytest -q
if errorlevel 1 (
  popd
  goto :failed
)
popd
pushd frontend
call npm run typecheck
if errorlevel 1 (
  popd
  goto :failed
)
popd

echo.
echo =====================================================
echo   Installation completed successfully.
echo   Run START_FORGEMIND.bat to open the application.
echo =====================================================
pause
exit /b 0

:failed
echo.
echo [ERROR] Installation stopped because a command failed.
echo Review the message above, then run SETUP_WINDOWS.bat again.
pause
exit /b 1
