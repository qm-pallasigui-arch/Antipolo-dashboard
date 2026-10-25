@echo off
rem Start the Antipolo monthly ICD-10 dashboard.
rem Close this window, or press Ctrl+C, to stop it.

setlocal
cd /d "%~dp0"

set "PYTHON=python"
if exist ".venv\Scripts\python.exe" set "PYTHON=%~dp0.venv\Scripts\python.exe"

"%PYTHON%" -c "import sys" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Could not run Python.
    echo Install Python 3.12+ and add it to PATH, or create a virtual
    echo environment in this folder with:  python -m venv .venv
    echo.
    pause
    exit /b 1
)

set "LOG_LEVEL=INFO"
set "PYTHONUNBUFFERED=1"
set "DASH_DEBUG=false"
set "HOST=127.0.0.1"
set "PORT=8050"

echo Starting the monthly ICD-10 dashboard
echo   URL   http://127.0.0.1:8050
echo   Stop  close this window, or press Ctrl+C
echo.

"%PYTHON%" app.py

echo.
echo The dashboard has stopped.
pause
