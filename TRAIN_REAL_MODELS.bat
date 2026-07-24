@echo off
setlocal EnableExtensions
cd /d "%~dp0backend"
title ForgeMind AI Real-Data Training

if not exist ".venv\Scripts\python.exe" (
  echo Python environment not found. Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"

echo.
echo =====================================================
echo   ForgeMind AI 3.0 - Real-Data Model Training
echo =====================================================
echo   1. MetroPT-3 air-compressor model
 echo   2. KolektorSDD visual quality model
 echo   3. Both models
 echo.
set /p CHOICE=Choose 1, 2, or 3:

if "%CHOICE%"=="1" goto metro
if "%CHOICE%"=="2" goto ksdd_license
if "%CHOICE%"=="3" goto both_license
echo Invalid choice.
pause
exit /b 1

:ksdd_license
echo.
echo KSDD is licensed CC BY-NC-SA 4.0.
echo Use it only for permitted non-commercial work or after obtaining commercial permission.
set /p ACCEPT=Type YES to confirm that you accept the dataset license:
if /I not "%ACCEPT%"=="YES" goto cancelled
goto ksdd

:both_license
echo.
echo KSDD is licensed CC BY-NC-SA 4.0.
echo Use it only for permitted non-commercial work or after obtaining commercial permission.
set /p ACCEPT=Type YES to confirm that you accept the dataset license:
if /I not "%ACCEPT%"=="YES" goto cancelled
goto both

:metro
set "METROCSV="
python ml\download_real_datasets.py metropt || goto fail
for /r ml\data\metropt %%F in (*MetroPT3*.csv) do set "METROCSV=%%F"
if not defined METROCSV (
  echo MetroPT CSV not found after extraction.
  goto fail
)
python ml\train_metropt.py "%METROCSV%" || goto fail
goto done

:ksdd
python ml\download_real_datasets.py ksdd --accept-ksdd-nc-license || goto fail
python ml\train_ksdd.py ml\data\ksdd || goto fail
goto done

:both
set "METROCSV="
python ml\download_real_datasets.py all --accept-ksdd-nc-license || goto fail
for /r ml\data\metropt %%F in (*MetroPT3*.csv) do set "METROCSV=%%F"
if not defined METROCSV (
  echo MetroPT CSV not found after extraction.
  goto fail
)
python ml\train_metropt.py "%METROCSV%" || goto fail
python ml\train_ksdd.py ml\data\ksdd || goto fail
goto done

:done
echo.
echo Training completed. Restart ForgeMind so the API loads the new model bundles.
pause
exit /b 0

:cancelled
echo Training cancelled. No dataset was downloaded.
pause
exit /b 0

:fail
echo.
echo Training stopped because a download, dataset layout, or model step failed.
echo Read docs\REAL_AI_MODELS.md for manual dataset placement and commands.
pause
exit /b 1
