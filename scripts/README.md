# scripts/ — run the whole stack with one command

Starts the **datastores** (Postgres/Redis/Neo4j/Mongo via docker), the **backend**
(FastAPI on `:8000`, `--reload`), and the **frontend** (Next.js dev on `:3000`).

## Windows
- **Start:** double-click `scripts\start.bat` (or run it from a terminal). Two windows
  open — one for the API, one for the web. Give them ~15s, then open
  <http://localhost:3000>.
- **Stop:** run `scripts\stop.bat` (or just close both windows).

## macOS / Linux / Git Bash
```bash
bash scripts/start.sh      # Ctrl+C stops both dev servers
bash scripts/stop.sh       # or stop them + the datastores later
```

## Git hooks (code-quality gate)
One-time per clone, enable the shared hooks in `.githooks/`:
```bash
scripts\setup-hooks.bat      # Windows
bash scripts/setup-hooks.sh  # macOS / Linux / Git Bash
```
This sets `core.hooksPath = .githooks`, giving you:
- **pre-commit** — `ruff` on staged `.py` + `tsc --noEmit` on the web app (only when relevant files are
  staged, so pre-existing debt never blocks you).
- **pre-push** — `pytest` (apps/api) before code leaves your machine.

Bypass a hook once, intentionally: `git commit --no-verify` / `git push --no-verify`.

## Notes
- **API port** is `8000` (matches `apps/web/.env.local` → `NEXT_PUBLIC_API_URL`). If
  `8000` is taken, edit `API_PORT` at the top of the script (and keep `.env.local` in
  sync) — e.g. `API_PORT=8001 bash scripts/start.sh`.
- **First run / after pulling:** install deps once — `uv sync` (repo root) and
  `cd apps/web && npm install`. The scripts don't reinstall on every start.
- The datastore step is best-effort: if Docker isn't running or the stores are
  already up, it's skipped and the backend just connects to whatever is on the
  configured ports (`.env`: Postgres 5433, Redis 6379, Mongo 27018).
- Never run `npm run build` while `npm run dev` is live — use `npx tsc --noEmit` to
  type-check instead.
