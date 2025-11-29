@echo off
REM Startup script for Recruitment Platform (Local Development)
REM This script starts all services needed for local development

echo ============================================================
echo   Recruitment Platform - Local Development Startup
echo   WITH VECTOR SEARCH + WEBSOCKET REAL-TIME UPDATES
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

REM Activate virtual environment and start Django with Daphne (WebSocket support)
echo [3/5] Starting Django with Daphne (WebSocket support) on port 8001...
start "Django Backend (Daphne)" cmd /k "cd /d %~dp0 && venv\Scripts\activate && daphne -b 0.0.0.0 -p 8001 recruitment_backend.asgi:application"
timeout /t 2 /nobreak >nul
echo      Django started with WebSocket support!
echo.

REM Start FastAPI
echo [4/5] Starting FastAPI on port 8000...
start "FastAPI Service" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python -m uvicorn app.main:app --reload --port 8000"
timeout /t 2 /nobreak >nul
echo      FastAPI started!
echo.

REM Start Celery Worker (with priority queues including dedicated embeddings queue)
echo [5/5] Starting Celery Worker (priority queues: high, embeddings, medium, low)...
echo      - High: Emails
echo      - Embeddings: Vector Search (dedicated, won't be blocked)
echo      - Medium: AI Analysis
echo      - Low: Maintenance
start "Celery Worker" cmd /k "cd /d %~dp0 && venv\Scripts\activate && celery -A recruitment_backend worker -Q high_priority,embeddings,medium_priority,low_priority -l info --pool=solo"
timeout /t 2 /nobreak >nul
echo      Celery Worker started with priority queues!
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
echo   Core Services:
echo   - Django Admin:      http://localhost:8001/admin
echo   - WebSocket Test:    http://localhost:8001/ws-test
echo   - FastAPI Docs:      http://localhost:8000/docs
echo   - Flower Dashboard:  http://localhost:5555
echo   - RabbitMQ UI:       http://localhost:15672 (guest/guest)
echo.
echo   Vector Search API Endpoints:
echo   - Search Candidates: POST http://localhost:8001/api/search/candidates/
echo   - Search Jobs:       POST http://localhost:8001/api/search/jobs/
echo   - Similar Candidates: POST http://localhost:8001/api/search/similar-candidates/
echo.
echo   Next Steps:
echo   1. Run migrations:        python manage.py migrate
echo   2. Generate embeddings:   python manage.py generate_embeddings --all
echo   3. Check status:          python manage.py generate_embeddings --stats
echo   4. Run tests:             python scripts\test_vector_search.py
echo   5. Test WebSockets:       Open http://localhost:8001/ws-test
echo.
echo   Press any key to view service status...
pause >nul

REM Show Docker service status
echo.
echo Docker Services Status:
docker-compose -f docker-compose.local.yml ps
echo.
echo ============================================================
echo   To stop all services, run: stop_all.bat
echo ============================================================
echo.
pause
