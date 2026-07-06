#!/usr/bin/env bash
# Laboratree — stop the backend + frontend dev servers and the datastores.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "Stopping backend + frontend..."
pkill -f "uvicorn laboratree.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true

echo "Stopping datastores (docker compose stop)..."
docker compose -f "$ROOT/infra/docker-compose.yml" stop 2>/dev/null || true

echo "Done."
