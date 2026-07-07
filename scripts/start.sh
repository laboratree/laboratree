#!/usr/bin/env bash
# ============================================================================
#  Laboratree — start the whole stack (datastores + backend + frontend).
#  Run:  bash scripts/start.sh   (Git Bash on Windows, or macOS/Linux)
#  Ctrl+C stops both dev servers.
# ============================================================================
set -uo pipefail

API_PORT="${API_PORT:-8000}"   # matches apps/web/.env.local; override: API_PORT=8001 bash scripts/start.sh
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo
echo "  Laboratree — starting up..."
echo "  API: http://localhost:${API_PORT}/health   Web: http://localhost:3000"
echo

echo "[1/3] Starting datastores (docker compose)..."
# Only the datastores — api/worker/web run locally below (uvicorn + npm), not in Docker.
docker compose -f "$ROOT/infra/docker-compose.yml" up -d postgres redis neo4j mongodb \
  || echo "  (skipped — docker not running or stores already up; backend will use whatever is on those ports)"

echo "[2/3] Starting backend (FastAPI, --reload)..."
( cd "$ROOT/apps/api" && uv run uvicorn laboratree.main:app --reload --port "$API_PORT" ) &
API_PID=$!

echo "[3/3] Starting frontend (Next.js dev)..."
( cd "$ROOT/apps/web" && npm run dev ) &
WEB_PID=$!

trap 'echo; echo "Stopping..."; kill "$API_PID" "$WEB_PID" 2>/dev/null || true' INT TERM
echo
echo "  Running. Open http://localhost:3000  (Ctrl+C to stop both)"
wait
