@echo off
echo.
echo ============================================
echo   LangOrch - First Time Setup (Docker)
echo ============================================
echo.
echo This script will:
echo   1. Setup database schema
echo   2. Create test users
echo   3. Start backend and frontend
echo.
pause

echo.
echo [1/4] Checking Docker services...
docker ps | findstr "langorch_postgres" >nul
if %errorlevel% neq 0 (
    echo [ERROR] Docker PostgreSQL is not running!
    echo Please run: docker-compose up -d
    pause
    exit /b 1
)
echo [OK] Docker services are running
echo.

echo [2/4] Setting up database...
cd backend
python -m alembic upgrade head
if %errorlevel% neq 0 (
    echo [ERROR] Migration failed. Installing dependencies...
    pip install -r requirements.txt
    python -m alembic upgrade head
)
echo [OK] Database schema created
echo.

echo [3/4] Creating test users...
python scripts\seed_test_data.py
echo [OK] Test users created
echo.

echo [4/4] Starting services...
echo.
echo ============================================
echo   Starting Backend and Frontend
echo ============================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/api/v1/docs
echo.
echo Test Credentials:
echo   Admin: admin@test.com / admin123
echo   User:  user@test.com / user123
echo ============================================
echo.

REM Start backend
start "LangOrch Backend" cmd /k "cd /d %cd% && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait for backend
timeout /t 3 /nobreak >nul

REM Start frontend
cd ..\frontend
start "LangOrch Frontend" cmd /k "npm run dev"

echo.
echo Services started in separate windows!
echo.
echo Next steps:
echo   1. Wait for both services to start (check the new windows)
echo   2. Open http://localhost:3000
echo   3. Login with admin@test.com / admin123
echo.
pause
