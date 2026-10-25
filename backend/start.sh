#!/bin/sh
set -eu
# Ensure DATA_DIR exists (required on ephemeral hosts like Render free tier)
mkdir -p "${DATA_DIR:-/tmp/data}"
# Railway supplies PORT; Render and Docker Compose default to 8000.
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}" --access-log
