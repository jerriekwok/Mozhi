@echo off
setlocal

set "ROOT=%~dp0"
set "PYTHON=%ROOT%.venv\Scripts\python.exe"

if not exist "%PYTHON%" (
    echo [Error] Virtual environment was not found: %PYTHON%
    echo Please create it first with: python -m venv .venv
    pause
    exit /b 1
)

echo Starting Mozhi backend on http://127.0.0.1:8000 ...
start "Mozhi Backend" /D "%ROOT%backend" cmd.exe /k ""%PYTHON%" -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000"

echo Starting Mozhi frontend on http://127.0.0.1:8080 ...
start "Mozhi Frontend" /D "%ROOT%" cmd.exe /k ""%PYTHON%" "%ROOT%frontend\server.py""

echo.
echo Mozhi is starting in two separate windows.
echo Frontend: http://127.0.0.1:8080
echo Backend docs: http://127.0.0.1:8000/docs
echo.
exit /b 0
