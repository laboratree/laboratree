@echo off
REM ============================================================================
REM  Laboratree — start the whole stack (datastores + backend + frontend).
REM  Double-click this file, or run:  scripts\start.bat
REM  Each service opens in its own window; close a window to stop that service.
REM ============================================================================
setlocal

REM API port (matches apps\web\.env.local NEXT_PUBLIC_API_URL). Change here if 8000 is taken.
set "API_PORT=8000"

REM Repo root = the folder that contains this scripts\ folder.
set "ROOT=%~dp0.."
pushd "%ROOT%"
set "ROOT=%CD%"
popd

echo.
echo   Laboratree — starting up...
echo   -----------------------------------------------------------------
echo   Datastores : postgres:5433 redis:6379 mongo:27018 (docker)
echo   Backend    : http://localhost:%API_PORT%/health
echo   Frontend   : http://localhost:3000
echo   -----------------------------------------------------------------
echo.

echo [1/3] Starting datastores (docker compose)...
REM Only the datastores — api/worker/web run locally below (uvicorn + npm), not in Docker.
docker compose -f "%ROOT%\infra\docker-compose.yml" up -d postgres redis neo4j mongodb
if errorlevel 1 (
  echo   ^(Skipping — docker not running or stores already up. Backend will use whatever is on those ports.^)
)

echo [2/3] Starting backend (FastAPI, --reload)...
start "Laboratree API" /d "%ROOT%\apps\api" cmd /k uv run uvicorn laboratree.main:app --reload --port %API_PORT%

echo [3/3] Starting frontend (Next.js dev)...
start "Laboratree Web" /d "%ROOT%\apps\web" cmd /k npm run dev

echo.
echo   Two windows opened (API + Web). Give them ~15s, then open:
echo       http://localhost:3000
echo.
echo   To stop: close both windows, or run  scripts\stop.bat
echo.
endlocal
