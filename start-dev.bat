@echo off
REM LangOrch Development Environment Startup Script (Windows)
REM Version 0.1 - MVP

echo.
echo ========================================
echo   LangOrch Development Environment
echo ========================================
echo.

REM Check if PostgreSQL is running
echo [1/5] Checking PostgreSQL...
psql -U postgres -c "SELECT 1;" >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] PostgreSQL is not running. Please start PostgreSQL first.
    pause
    exit /b 1
)
echo [OK] PostgreSQL is running
echo.

REM Check if database exists
echo [2/5] Checking database...
psql -U postgres -lqt | findstr /C:"langorch" >nul 2>&1
if %errorlevel% neq 0 (
    echo Creating database 'langorch'...
    psql -U postgres -c "CREATE DATABASE langorch;"
    psql -U postgres -c "CREATE USER langorch WITH PASSWORD 'langorch123';"
    psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE langorch TO langorch;"
    echo [OK] Database created
) else (
    echo [OK] Database 'langorch' exists
)
echo.

REM Run migrations
echo [3/5] Running database migrations...
cd backend
call alembic upgrade head
if %errorlevel% neq 0 (
    echo [ERROR] Migration failed
    pause
    exit /b 1
)
echo [OK] Migrations completed
echo.

REM Seed test data
echo [4/5] Seeding test data...
python scripts\seed_test_data.py
echo [OK] Test data seeded
echo.

REM Start services
echo [5/5] Starting services...
echo.
echo ========================================
echo   Services Starting
echo ========================================
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo API Docs: http://localhost:8000/api/v1/docs
echo.
echo Test Credentials:
echo   Admin: admin@test.com / admin123
echo   User:  user@test.com / user123
echo.
echo Press Ctrl+C to stop all services
echo ========================================
echo.

REM Start backend in new window
start "LangOrch Backend" cmd /k "cd /d %cd% && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"

REM Wait a bit for backend to start
timeout /t 3 /nobreak >nul

REM Start frontend in new window
cd ..\frontend
start "LangOrch Frontend" cmd /k "npm run dev"

echo.
echo Services started in separate windows
echo Close those windows to stop the services
echo.
pause
