#!/bin/sh
set -eu
# Railway supplies PORT; Docker Compose defaults to 8000.
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --access-log
