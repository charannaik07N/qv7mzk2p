#!/bin/sh
# Local-only launcher. Production does not enable the loopback refresh route.
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ ! -x .venv/bin/python ]; then
  echo 'Create the Python 3.12 environment and install backend/requirements.txt first.' >&2
  exit 1
fi
if [ ! -x frontend/node_modules/.bin/vite ]; then
  (cd frontend && npm install)
fi
cleanup() {
  if [ -n "${wind_api_pid:-}" ]; then kill "$wind_api_pid" 2>/dev/null || true; fi
  if [ -n "${wind_frontend_pid:-}" ]; then kill "$wind_frontend_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM
ENABLE_LOCAL_REFRESH=1 AUTO_REFRESH_ON_STARTUP=1 .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 &
wind_api_pid=$!
(cd frontend && npm run dev -- --host 127.0.0.1 --strictPort) &
wind_frontend_pid=$!
echo 'WindMarket: http://localhost:5173 — API: http://127.0.0.1:8000/docs'
echo 'Official data will load in the background if no snapshot exists. Ctrl+C stops both services.'
# Exit if either service stops rather than leaving an orphaned process.
while kill -0 "$wind_api_pid" 2>/dev/null && kill -0 "$wind_frontend_pid" 2>/dev/null; do sleep 1; done
exit 1
