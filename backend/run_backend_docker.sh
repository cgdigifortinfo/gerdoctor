#!/usr/bin/env sh
set -eu

python -m pip install --no-cache-dir -r requirements.txt
exec python -m uvicorn server:app --host 0.0.0.0 --port 8001
