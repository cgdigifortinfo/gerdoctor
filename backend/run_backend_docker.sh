#!/usr/bin/env sh
set -eu

grep -v '^emergentintegrations==' requirements.txt > /tmp/requirements-local.txt
python -m pip install --no-cache-dir -r /tmp/requirements-local.txt
exec python -m uvicorn server:app --host 0.0.0.0 --port 8001
