@echo off
REM Stop script for Recruitment Platform (Local Development)

echo ============================================================
echo   Stopping All Services
echo ============================================================
echo.

REM Stop Docker services
echo [1/2] Stopping Docker services...
docker-compose -f docker-compose.local.yml stop
echo      Docker services stopped!
echo.

REM Kill local services
echo [2/2] Stopping local services (Django, FastAPI, Celery, Flower)...

REM Kill Python processes (Django, FastAPI)
taskkill /FI "WINDOWTITLE eq Django Backend*" /T /F 2>nul
taskkill /FI "WINDOWTITLE eq FastAPI Service*" /T /F 2>nul

REM Kill Celery processes
taskkill /FI "WINDOWTITLE eq Celery Worker*" /T /F 2>nul
taskkill /FI "WINDOWTITLE eq Flower Dashboard*" /T /F 2>nul

REM Fallback: kill any remaining celery processes
taskkill /F /IM celery.exe 2>nul

echo      Local services stopped!
echo.

echo ============================================================
echo   ALL SERVICES STOPPED
echo ============================================================
echo.
pause
