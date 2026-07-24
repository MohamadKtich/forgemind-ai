@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title ForgeMind AI Verification
if not exist "backend\.venv\Scripts\python.exe" (
  echo Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)

echo Running release secret preflight...
python scripts\preflight_release.py
if errorlevel 1 (
  echo Secret preflight failed.
  pause
  exit /b 1
)

echo Running backend integration tests...
pushd backend
call ".venv\Scripts\activate.bat"
python -m compileall app ml
if errorlevel 1 goto :failed_backend
python -m pytest -q
if errorlevel 1 goto :failed_backend
popd

echo Running TypeScript validation...
pushd frontend
call npm run typecheck
if errorlevel 1 goto :failed_frontend

echo Running Next.js production build...
call npm run build
if errorlevel 1 goto :failed_frontend
popd

echo.
echo All ForgeMind verification checks passed.
pause
exit /b 0

:failed_backend
popd
echo Backend verification failed.
pause
exit /b 1

:failed_frontend
popd
echo Frontend verification failed.
pause
exit /b 1
