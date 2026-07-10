@echo off
REM ============================================================================
REM  Laboratree — stop everything: kills the API/Web dev servers + datastores.
REM ============================================================================
setlocal

set "ROOT=%~dp0.."
pushd "%ROOT%"
set "ROOT=%CD%"
popd

echo Stopping frontend + backend dev servers...
REM Close the titled windows started by start.bat (best-effort).
taskkill /FI "WINDOWTITLE eq Laboratree API*" /T /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Laboratree Web*" /T /F >nul 2>&1

echo Stopping datastores (docker compose down)...
docker compose -f "%ROOT%\infra\docker-compose.yml" stop >nul 2>&1

echo Done.
endlocal
