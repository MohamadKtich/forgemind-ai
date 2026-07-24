@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Backend environment is missing. Run ..\SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python -m fastapi dev app/main.py --host 127.0.0.1 --port 8000
