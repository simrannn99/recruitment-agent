@echo off
REM Startup script for Recruitment Platform (Local Development)
REM This script starts all services needed for local development

echo ============================================================
echo   Recruitment Platform - Local Development Startup
echo ============================================================
echo.

REM Start Docker services (PostgreSQL, RabbitMQ, Redis)
echo [1/5] Starting Docker services (PostgreSQL, RabbitMQ, Redis)...
docker-compose -f docker-compose.local.yml up -d
if %errorlevel% neq 0 (
    echo ERROR: Failed to start Docker services
    pause
    exit /b 1
)
echo      Docker services started successfully!
echo.

REM Wait for services to be ready
echo [2/5] Waiting for services to be ready...
timeout /t 5 /nobreak >nul
echo      Services ready!
echo.

REM Activate virtual environment and start Django
echo [3/5] Starting Django on port 8001...
start "Django Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python manage.py runserver 8001"
timeout /t 2 /nobreak >nul
echo      Django started!
echo.

REM Start FastAPI
echo [4/5] Starting FastAPI on port 8000...
start "FastAPI Service" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
echo      FastAPI started!
echo.

REM Start Celery Worker
echo [5/5] Starting Celery Worker...
start "Celery Worker" cmd /k "cd /d %~dp0 && venv\Scripts\activate && celery -A recruitment_backend worker -l info --pool=solo"
timeout /t 2 /nobreak >nul
echo      Celery Worker started!
echo.

REM Start Flower (optional)
echo [BONUS] Starting Flower monitoring on port 5555...
start "Flower Dashboard" cmd /k "cd /d %~dp0 && venv\Scripts\activate && celery -A recruitment_backend flower --port=5555"
timeout /t 2 /nobreak >nul
echo      Flower started!
echo.

echo ============================================================
echo   ALL SERVICES STARTED SUCCESSFULLY!
echo ============================================================
echo.
echo   Services running:
echo   - Django Admin:      http://localhost:8001/admin
echo   - FastAPI Docs:      http://localhost:8000/docs
echo   - Flower Dashboard:  http://localhost:5555
echo   - RabbitMQ UI:       http://localhost:15672 (guest/guest)
echo.
echo   Press any key to view service status...
pause >nul

REM Show Docker service status
echo.
echo Docker Services Status:
docker-compose -f docker-compose.local.yml ps
echo.
echo ============================================================
echo   To stop all services, run: stop_services.bat
echo ============================================================
echo.
pause
