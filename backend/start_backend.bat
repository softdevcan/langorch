@echo off
echo.
echo ========================================
echo   Starting LangOrch Backend
echo ========================================
echo.

REM Use venv Python
set PYTHON=%~dp0..\venv\Scripts\python.exe
set UVICORN=%~dp0..\venv\Scripts\uvicorn.exe

REM Check if venv exists
if not exist "%PYTHON%" (
    echo [ERROR] Virtual environment not found!
    echo Please create venv first: python -m venv venv
    pause
    exit /b 1
)

echo Using Python: %PYTHON%
%PYTHON% --version
echo.

REM Start uvicorn with venv
echo Starting backend on http://0.0.0.0:8000
echo API Docs: http://localhost:8000/api/v1/docs
echo.

cd /d "%~dp0"
"%UVICORN%" app.main:app --reload --host 0.0.0.0 --port 8000
