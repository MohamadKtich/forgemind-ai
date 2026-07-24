@echo off
cd /d "%~dp0"
if not exist "node_modules" (
  echo Frontend packages are missing. Run ..\SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
call npm run dev
